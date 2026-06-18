"""
TRINKER - Build Order Importer
Handles fetching and parsing build orders from external sources:
  - buildorderguide.com (URL paste → auto-fetch)
  - JSON files (TRINKER native + generic)
  - Plain .txt files (legacy RTS_Overlay format)

Each importer returns a BuildOrder dataclass on success, raises on failure.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..core.config import CACHE_DIR, REQUEST_HEADERS, REQUEST_TIMEOUT
from ..core.logger import logger
from .models import BuildOrder, BuildStep

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mmss_to_sec(time_str: str) -> int:
    """
    Convert 'M:SS' or 'MM:SS' string to total seconds.
    Returns 0 if parsing fails.
    """
    try:
        parts = time_str.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 1:
            return int(parts[0])
    except Exception:
        pass
    return 0


def _get(url: str, *, cache_key: Optional[str] = None) -> str:
    """
    Perform a GET request with optional caching.
    Cached HTML is stored in CACHE_DIR for offline use.
    Also checks data/buildorderguide_cache/ from sync_buildorderguide.py.
    """
    if cache_key:
        slug = cache_key.replace("bog_", "", 1) if cache_key.startswith("bog_") else cache_key
        sync_cache = Path(__file__).resolve().parents[2] / "data" / "buildorderguide_cache" / f"{slug}.html"
        if sync_cache.exists():
            logger.debug("Sync cache hit: %s", slug)
            return sync_cache.read_text(encoding="utf-8")

        cache_path = CACHE_DIR / f"{cache_key}.html"
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < 86400:  # 24-hour cache
                logger.debug("Cache hit: %s", cache_key)
                return cache_path.read_text(encoding="utf-8")

    logger.info("Fetching: %s", url)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    html = resp.text

    if cache_key:
        cache_path = CACHE_DIR / f"{cache_key}.html"
        cache_path.write_text(html, encoding="utf-8")

    return html


# ---------------------------------------------------------------------------
# buildorderguide.com importer
# ---------------------------------------------------------------------------


def import_from_buildorderguide(url: str) -> BuildOrder:
    """
    Fetch and parse a build order from buildorderguide.com.

    Supported URL patterns:
      https://www.buildorderguide.com/builds/<slug>
      https://buildorderguide.com/builds/<slug>

    Args:
        url: Full URL to the build order page.

    Returns:
        Parsed BuildOrder instance.

    Raises:
        ValueError: If the URL is not a valid buildorderguide.com build URL.
        requests.HTTPError: If the page cannot be fetched.
        RuntimeError: If parsing fails (page structure changed).
    """
    parsed = urlparse(url)
    if "buildorderguide.com" not in parsed.netloc:
        raise ValueError(f"Not a buildorderguide.com URL: {url}")

    # Extract slug for cache key
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2 or path_parts[0] != "builds":
        raise ValueError(
            f"Expected URL like https://www.buildorderguide.com/builds/<slug>, got: {url}"
        )
    slug = path_parts[1]

    html = _get(url, cache_key=f"bog_{slug}")
    soup = BeautifulSoup(html, "html.parser")

    # ── Metadata ──────────────────────────────────────────────────────────────
    name = _extract_text(soup, "h1") or slug
    civ = _extract_meta_or_tag(soup, "civ") or "Any"

    # Strategy / description lives in various meta containers depending on page version
    strategy = ""
    notes = ""
    desc_el = soup.find(class_=re.compile(r"description|overview|intro", re.I))
    if desc_el:
        notes = desc_el.get_text(separator=" ", strip=True)

    # Try to extract author
    author = ""
    author_el = soup.find(class_=re.compile(r"author|creator|submitted", re.I))
    if author_el:
        author = author_el.get_text(strip=True)

    # ── Steps ─────────────────────────────────────────────────────────────────
    steps = _parse_bog_steps(soup)
    if not steps:
        # Fallback: try generic table/list parsing
        steps = _parse_generic_steps(soup)

    if not steps:
        # Site now stores builds in Firestore; detail pages are client-rendered modals.
        try:
            from .bog_firestore import import_build_from_firestore

            logger.info("HTML parse empty for %s — fetching Firestore document", slug)
            return import_build_from_firestore(slug)
        except Exception as exc:
            logger.debug("Firestore fallback failed for %s: %s", slug, exc)

    if not steps:
        raise RuntimeError(
            "Could not parse build steps from buildorderguide.com — "
            "the page structure may have changed. Try the manual editor."
        )

    bo = BuildOrder(
        name=name,
        civ=civ,
        strategy=strategy or _infer_strategy(name),
        author=author,
        source_url=url,
        external_id=slug,
        steps=steps,
        notes=notes,
        tags=_infer_tags(name, civ, strategy),
    )
    logger.info("Imported '%s' (%d steps) from buildorderguide.com", bo.name, len(bo.steps))
    return bo


def _extract_text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.find(selector)
    return el.get_text(strip=True) if el else ""


def _extract_meta_or_tag(soup: BeautifulSoup, keyword: str) -> str:
    # Try data attributes first
    el = soup.find(attrs={f"data-{keyword}": True})
    if el:
        return el[f"data-{keyword}"]
    # Try class-based containers
    el = soup.find(class_=re.compile(keyword, re.I))
    return el.get_text(strip=True) if el else ""


def _parse_bog_steps(soup: BeautifulSoup) -> list[BuildStep]:
    """
    Parse steps from the standard buildorderguide.com step table/list structure.
    The site uses a React frontend; steps are serialized in a <script id="__NEXT_DATA__">.
    """
    steps: list[BuildStep] = []

    # Try Next.js data blob first (most reliable)
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if next_data_tag:
        try:
            data = json.loads(next_data_tag.string)
            # Navigate the Next.js page props to find the build order data
            props = data.get("props", {}).get("pageProps", {})
            build = props.get("build") or props.get("buildOrder") or {}
            raw_steps = build.get("steps") or build.get("buildSteps") or []
            for i, s in enumerate(raw_steps, start=1):
                step = BuildStep(
                    index=i,
                    description=s.get("description") or s.get("text") or s.get("action") or "",
                    time_str=str(s.get("time") or s.get("gameTime") or ""),
                    population=int(s.get("population") or s.get("pop") or 0),
                    food=_int_or_none(s.get("food")),
                    wood=_int_or_none(s.get("wood")),
                    gold=_int_or_none(s.get("gold")),
                    stone=_int_or_none(s.get("stone")),
                    notes=s.get("notes") or s.get("hint") or "",
                    age=s.get("age"),
                )
                step.time_sec = _mmss_to_sec(step.time_str)
                steps.append(step)
            if steps:
                return steps
        except Exception as exc:
            logger.debug("Next.js data parse failed: %s", exc)

    # Fallback: HTML table rows
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # skip header
        for i, row in enumerate(rows, start=1):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            texts = [c.get_text(strip=True) for c in cells]
            step = BuildStep(index=i, description=texts[-1])
            if len(texts) >= 3:
                step.time_str = texts[0]
                step.time_sec = _mmss_to_sec(texts[0])
                step.population = _safe_int(texts[1])
            steps.append(step)

    return steps


def _parse_generic_steps(soup: BeautifulSoup) -> list[BuildStep]:
    """Last-resort: extract step-like list items from any ordered/unordered list."""
    steps = []
    lists = soup.find_all(["ol", "ul"])
    best_list = max(lists, key=lambda l: len(l.find_all("li")), default=None)
    if best_list:
        for i, li in enumerate(best_list.find_all("li"), start=1):
            text = li.get_text(strip=True)
            if len(text) > 5:
                steps.append(BuildStep(index=i, description=text))
    return steps


def _infer_strategy(name: str) -> str:
    name_l = name.lower()
    if "fast castle" in name_l or "fc" in name_l:
        return "Fast Castle"
    if "scout" in name_l:
        return "Scout Rush"
    if "archer" in name_l:
        return "Archer Rush"
    if "drush" in name_l:
        return "Drush"
    if "boom" in name_l:
        return "Boom"
    if "fast imp" in name_l or "fi " in name_l:
        return "Fast Imperial"
    return "Custom"


def _infer_tags(name: str, civ: str, strategy: str) -> list[str]:
    tags = []
    name_l = (name + " " + strategy).lower()
    for kw in [
        "rush",
        "castle",
        "boom",
        "knight",
        "archer",
        "scout",
        "drush",
        "monk",
        "siege",
    ]:
        if kw in name_l:
            tags.append(kw)
    if civ and civ.lower() not in ("any", ""):
        tags.append(civ.lower())
    return list(set(tags))


def _int_or_none(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _safe_int(s: str, default: int = 0) -> int:
    try:
        return int(re.sub(r"[^\d]", "", s))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# JSON importer (TRINKER native format)
# ---------------------------------------------------------------------------


def import_from_json_file(path: str | Path) -> BuildOrder:
    """
    Load a build order from a JSON file.
    Supports TRINKER's native format and a generic {name, steps} dict.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    # Handle list of steps at top level (bare steps format)
    if isinstance(data, list):
        data = {"name": path.stem, "steps": data}

    steps_raw = data.pop("steps", [])
    steps = []
    for i, s in enumerate(steps_raw, start=1):
        if isinstance(s, str):
            steps.append(BuildStep(index=i, description=s))
        else:
            step = BuildStep.from_dict({"index": i, **s})
            step.time_sec = step.time_sec or _mmss_to_sec(step.time_str)
            steps.append(step)

    bo = BuildOrder.from_dict({**data, "steps": []})
    bo.steps = steps
    bo.source_url = bo.source_url or str(path)
    logger.info("Loaded '%s' from JSON (%d steps)", bo.name, len(bo.steps))
    return bo


# ---------------------------------------------------------------------------
# Plain-text importer (legacy RTS_Overlay .txt format)
# ---------------------------------------------------------------------------


def import_from_txt_file(path: str | Path) -> BuildOrder:
    """
    Parse a plain-text build order file (one step per line).
    Lines starting with '#' are treated as comments / metadata.
    Format loosely: [TIME] [POP] Description
    """
    path = Path(path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    name = path.stem
    steps: list[BuildStep] = []
    civ = "Any"
    strategy = ""
    notes_lines: list[str] = []

    step_idx = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            comment = line.lstrip("#").strip()
            if ":" in comment:
                key, _, val = comment.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if key in ("name", "title"):
                    name = val
                elif key == "civ":
                    civ = val
                elif key == "strategy":
                    strategy = val
                else:
                    notes_lines.append(comment)
            else:
                notes_lines.append(comment)
            continue

        # Try to parse leading time token like "2:30" or "[2:30]"
        time_str = ""
        time_sec = 0
        m = re.match(r"^\[?(\d{1,2}:\d{2})\]?\s*", line)
        if m:
            time_str = m.group(1)
            time_sec = _mmss_to_sec(time_str)
            line = line[m.end() :]

        # Try pop count (bare integer before description)
        pop = 0
        m2 = re.match(r"^(\d{1,3})\s+", line)
        if m2 and int(m2.group(1)) < 300:
            pop = int(m2.group(1))
            line = line[m2.end() :]

        steps.append(
            BuildStep(
                index=step_idx,
                description=line,
                time_str=time_str,
                time_sec=time_sec,
                population=pop,
            )
        )
        step_idx += 1

    bo = BuildOrder(
        name=name,
        civ=civ,
        strategy=strategy,
        steps=steps,
        notes="\n".join(notes_lines),
        source_url=str(path),
    )
    logger.info("Loaded '%s' from TXT (%d steps)", bo.name, len(bo.steps))
    return bo


# ---------------------------------------------------------------------------
# Multi-source URL import (tries each source until one succeeds)
# ---------------------------------------------------------------------------


def _finalize_import(bo: BuildOrder) -> BuildOrder:
    """Apply enrichment and age inference to imported build orders."""
    from .step_enricher import enrich_steps, infer_age_from_text

    for step in bo.steps:
        if not step.age:
            step.age = infer_age_from_text(step.description)
        if step.time_str and not step.time_sec:
            step.time_sec = _mmss_to_sec(step.time_str)
    bo.steps = enrich_steps(bo.steps)
    return bo


def import_from_aoe2guides(url: str) -> BuildOrder:
    """Parse build orders from aoe2guides.com-style pages."""
    parsed = urlparse(url)
    if "aoe2guides" not in parsed.netloc:
        raise ValueError(f"Not an aoe2guides.com URL: {url}")

    slug = parsed.path.strip("/").split("/")[-1] or "build"
    html = _get(url, cache_key=f"aoe2g_{slug}")
    soup = BeautifulSoup(html, "html.parser")

    name = _extract_text(soup, "h1") or slug.replace("-", " ").title()
    steps = _parse_bog_steps(soup) or _parse_generic_steps(soup)
    if not steps:
        raise RuntimeError("Could not parse steps from aoe2guides.com")

    bo = BuildOrder(
        name=name,
        civ="Any",
        strategy=_infer_strategy(name),
        source_url=url,
        external_id=f"aoe2g_{slug}",
        steps=steps,
        tags=_infer_tags(name, "Any", ""),
    )
    return _finalize_import(bo)


def import_from_spreadsheet_json(url: str) -> BuildOrder:
    """
    Import from public Google Sheets JSON export or raw JSON build-order URLs.
    """
    if "docs.google.com" in url:
        m = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if m:
            sheet_id = m.group(1)
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json"

    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = resp.text
    if text.startswith("/*"):
        text = text[text.find("{") : text.rfind("}") + 1]

    data = json.loads(text)
    rows = data if isinstance(data, list) else data.get("rows") or data.get("steps") or []
    steps: list[BuildStep] = []
    name = data.get("name", "Imported Build") if isinstance(data, dict) else "Imported Build"

    for i, row in enumerate(rows, start=1):
        if isinstance(row, str):
            steps.append(BuildStep(index=i, description=row))
        elif isinstance(row, dict):
            desc = row.get("description") or row.get("step") or row.get("c", "")
            if not desc:
                continue
            steps.append(
                BuildStep(
                    index=i,
                    description=str(desc),
                    time_str=str(row.get("time") or row.get("time_str") or ""),
                    population=int(row.get("pop") or row.get("population") or 0),
                )
            )

    if not steps:
        raise RuntimeError("No steps found in spreadsheet/JSON URL")

    bo = BuildOrder(name=name, civ="Any", source_url=url, steps=steps)
    return _finalize_import(bo)


def import_from_url(url: str) -> BuildOrder:
    """
    Import a build order from any supported URL.
    Tries multiple sources in order until one succeeds.

    Supported:
      - buildorderguide.com
      - aoe2guides.com
      - Google Sheets / raw JSON URLs
    """
    url = url.strip()
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    sources: list[tuple[str, callable]] = []

    if "buildorderguide.com" in host:
        sources.append(("buildorderguide.com", import_from_buildorderguide))
    if "aoe2guides" in host:
        sources.append(("aoe2guides.com", import_from_aoe2guides))
    if any(x in host for x in ("docs.google.com", "raw.githubusercontent.com")) or url.endswith(
        ".json"
    ):
        sources.append(("JSON/Sheets", import_from_spreadsheet_json))

    # Unknown host — try all parsers
    if not sources:
        sources = [
            ("buildorderguide.com", import_from_buildorderguide),
            ("aoe2guides.com", import_from_aoe2guides),
            ("generic HTML", lambda u: _finalize_import(_import_generic_html(u))),
            ("JSON/Sheets", import_from_spreadsheet_json),
        ]

    errors: list[str] = []
    for label, fn in sources:
        try:
            bo = fn(url)
            logger.info("Imported '%s' from %s (%d steps)", bo.name, label, len(bo.steps))
            return bo
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            logger.debug("Import via %s failed: %s", label, exc)

    raise RuntimeError("Could not import from any source.\n" + "\n".join(errors))


def _import_generic_html(url: str) -> BuildOrder:
    """Last-resort: pull title + list items from any build-order-like page."""
    html = _get(url, cache_key=f"generic_{hash(url) % 10**8}")
    soup = BeautifulSoup(html, "html.parser")
    name = _extract_text(soup, "h1") or urlparse(url).path.split("/")[-1]
    steps = _parse_bog_steps(soup) or _parse_generic_steps(soup)
    if not steps:
        raise RuntimeError("No steps found on page")
    return BuildOrder(
        name=name,
        civ="Any",
        strategy=_infer_strategy(name),
        source_url=url,
        steps=steps,
    )
