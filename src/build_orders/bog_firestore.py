"""
buildorderguide.com Firestore API client.

The site moved to a card/modal UI backed by Firebase Firestore (collection
``published-builds``). HTML listing pages no longer expose build URLs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from ..core.config import (
    BOG_FIRESTORE_API_KEY,
    BOG_FIRESTORE_PROJECT,
    BUILDORDERGUIDE_BASE,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
)
from ..core.logger import logger
from .models import BuildOrder, BuildStep

_CACHE_CHUNK = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "buildorderguide_cache"
    / "_chunk_466a38cabb506e57.js"
)

_DIFFICULTY = {1: "Easy", 2: "Medium", 3: "Hard"}


def _api_key() -> str:
    if BOG_FIRESTORE_API_KEY:
        return BOG_FIRESTORE_API_KEY
    if _CACHE_CHUNK.exists():
        text = _CACHE_CHUNK.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'apiKey:"([^"]+)"', text)
        if m:
            return m.group(1)
    raise RuntimeError("buildorderguide Firestore apiKey not configured")


def _project_id() -> str:
    if BOG_FIRESTORE_PROJECT:
        return BOG_FIRESTORE_PROJECT
    if _CACHE_CHUNK.exists():
        text = _CACHE_CHUNK.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'projectId:"([^"]+)"', text)
        if m:
            return m.group(1)
    raise RuntimeError("buildorderguide Firestore projectId not configured")


def _firestore_base() -> str:
    return (
        f"https://firestore.googleapis.com/v1/projects/{_project_id()}"
        "/databases/(default)/documents"
    )


def decode_firestore_value(raw: dict[str, Any]) -> Any:
    if "stringValue" in raw:
        return raw["stringValue"]
    if "integerValue" in raw:
        return int(raw["integerValue"])
    if "doubleValue" in raw:
        return float(raw["doubleValue"])
    if "booleanValue" in raw:
        return raw["booleanValue"]
    if "nullValue" in raw:
        return None
    if "timestampValue" in raw:
        return raw["timestampValue"]
    if "arrayValue" in raw:
        return [
            decode_firestore_value(v)
            for v in raw["arrayValue"].get("values", [])
        ]
    if "mapValue" in raw:
        return {
            k: decode_firestore_value(v)
            for k, v in raw["mapValue"].get("fields", {}).items()
        }
    return None


def decode_firestore_doc(doc: dict[str, Any]) -> dict[str, Any]:
    doc_id = doc.get("name", "").rsplit("/", 1)[-1]
    fields = {k: decode_firestore_value(v) for k, v in doc.get("fields", {}).items()}
    fields["id"] = doc_id
    return fields


def _label(value: str) -> str:
    if not value:
        return ""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return spaced.replace("_", " ").strip().title()


def _buildings_text(buildings: list[dict[str, Any]] | None) -> str:
    if not buildings:
        return ""
    parts = []
    for b in buildings:
        count = b.get("count") or 1
        btype = _label(str(b.get("type") or "building"))
        parts.append(f"build {count}x {btype}")
    return "; ".join(parts)


def _step_count(step: dict[str, Any]) -> int | str:
    raw = step.get("count")
    if raw is None:
        return 1
    try:
        return int(raw)
    except (TypeError, ValueError):
        return str(raw)


def bog_step_to_description(step: dict[str, Any]) -> str:
    """Convert a typed buildorderguide step object to overlay text."""
    stype = step.get("type") or ""
    count = _step_count(step)
    buildings = _buildings_text(step.get("buildings"))

    if stype == "newVillagers":
        task = _label(str(step.get("task") or ""))
        base = f"Queue {count} vill(s) on {task}" if task else f"Queue {count} villager(s)"
        return f"{base}; {buildings}" if buildings else base

    if stype == "moveVillagers":
        src = _label(str(step.get("from") or ""))
        dst = _label(str(step.get("to") or ""))
        base = f"Move {count} vill(s) from {src} to {dst}"
        return f"{base}; {buildings}" if buildings else base

    if stype == "lure":
        animal = _label(str(step.get("animal") or "boar"))
        return f"Lure {animal} to TC"

    if stype == "research":
        techs = step.get("tech") or []
        names = ", ".join(_label(str(t)) for t in techs) or "upgrade"
        return f"Research {names}"

    if stype == "ageUp":
        age = _label(str(step.get("age") or "feudal age"))
        return f"Click {age}"

    if stype == "newAge":
        age = _label(str(step.get("age") or "next age"))
        return f"Reach {age}"

    if stype == "build":
        return buildings or "Build production building"

    if stype == "trainUnit":
        unit = _label(str(step.get("unit") or "unit"))
        return f"Train {count}x {unit}"

    if stype == "collectGold":
        return f"Collect gold ({step.get('task') or 'task'})"

    if stype == "custom":
        return str(step.get("text") or "Custom step").strip()

    if stype == "decision":
        return str(step.get("text") or "Decision branch").strip()

    if stype == "trade":
        action = _label(str(step.get("action") or "trade"))
        resource = _label(str(step.get("resource") or "resource"))
        return f"{action} {resource}"

    return stype.replace("_", " ").title() or "Step"


def _resources_at_step(step: dict[str, Any]) -> dict[str, int]:
    resources = step.get("resources") or {}
    out: dict[str, int] = {}
    for key in ("food", "wood", "gold", "stone"):
        val = resources.get(key)
        if val is not None:
            out[key] = int(val)
    pop = resources.get("population") or resources.get("pop")
    if pop is not None:
        out["population"] = int(pop)
    return out


def steps_from_bog_build(raw_steps: list[dict[str, Any]]) -> list[BuildStep]:
    steps: list[BuildStep] = []
    for i, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, dict):
            continue
        resources = _resources_at_step(raw)
        steps.append(
            BuildStep(
                index=i,
                description=bog_step_to_description(raw),
                population=int(resources.get("population") or 0),
                food=resources.get("food"),
                wood=resources.get("wood"),
                gold=resources.get("gold"),
                stone=resources.get("stone"),
                age=raw.get("age"),
            )
        )
    return steps


def build_order_from_bog_data(data: dict[str, Any]) -> BuildOrder:
    build_id = str(data.get("id") or "")
    title = str(data.get("title") or build_id or "Untitled Build")
    civ = str(data.get("civilization") or "Any")
    author = str(data.get("author") or "")
    notes = str(data.get("description") or "")
    reference = str(data.get("reference") or "")
    if reference and reference not in notes:
        notes = f"{notes}\nReference: {reference}".strip()

    raw_steps = data.get("build") or []
    steps = steps_from_bog_build(raw_steps)
    if not steps:
        raise RuntimeError(f"No steps in build {build_id}")

    diff_raw = data.get("difficulty")
    difficulty = _DIFFICULTY.get(int(diff_raw), "Medium") if diff_raw is not None else "Medium"

    return BuildOrder(
        name=title,
        civ=civ,
        strategy=_infer_strategy(title),
        difficulty=difficulty,
        author=author,
        source_url=f"{BUILDORDERGUIDE_BASE}/builds/{build_id}",
        external_id=build_id,
        steps=steps,
        notes=notes,
        tags=_infer_tags(title, civ),
    )


def _infer_strategy(name: str) -> str:
    name_l = name.lower()
    for key, label in (
        ("fast castle", "Fast Castle"),
        ("fc ", "Fast Castle"),
        ("scout", "Scout Rush"),
        ("archer", "Archer Rush"),
        ("drush", "Drush"),
        ("boom", "Boom"),
        ("fast imp", "Fast Imperial"),
    ):
        if key in name_l:
            return label
    return "Custom"


def _infer_tags(name: str, civ: str) -> list[str]:
    tags: list[str] = []
    name_l = name.lower()
    for kw in ("rush", "castle", "boom", "knight", "archer", "scout", "drush", "monk", "siege"):
        if kw in name_l:
            tags.append(kw)
    if civ and civ.lower() not in ("any", "generic", ""):
        tags.append(civ.lower())
    return list(set(tags))


def fetch_published_build(build_id: str) -> dict[str, Any]:
    """Fetch one published build document by Firestore id."""
    url = f"{_firestore_base()}/published-builds/{quote(build_id, safe='')}?key={_api_key()}"
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = decode_firestore_doc(resp.json())
    status = data.get("status")
    if status not in ("published", "changed"):
        raise RuntimeError(f"Build {build_id} is not published (status={status!r})")
    return data


def discover_published_build_ids(*, page_size: int = 100) -> list[str]:
    """List all published/changed build ids from Firestore."""
    ids: list[str] = []
    page_token: str | None = None
    base = _firestore_base()
    key = _api_key()

    while True:
        url = f"{base}/published-builds?pageSize={page_size}&key={key}"
        if page_token:
            url += f"&pageToken={quote(page_token, safe='')}"
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        for doc in payload.get("documents") or []:
            data = decode_firestore_doc(doc)
            if data.get("status") in ("published", "changed"):
                ids.append(data["id"])
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    logger.info("Discovered %d published buildorderguide builds via Firestore", len(ids))
    return sorted(set(ids))


def discover_build_urls() -> list[str]:
    return [f"{BUILDORDERGUIDE_BASE}/builds/{bid}" for bid in discover_published_build_ids()]


def import_build_from_firestore(build_id: str) -> BuildOrder:
    data = fetch_published_build(build_id)
    return build_order_from_bog_data(data)


def cache_build_json(build_id: str, data: dict[str, Any], cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{build_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
