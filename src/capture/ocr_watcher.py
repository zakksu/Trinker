"""
TRINKER - Optional OCR Game-State Watcher
Captures small screen regions (resources, scoreboard) when replay parsing is insufficient.

Requires optional deps: mss, pillow, easyocr (or pytesseract).
Enable in Settings → OCR Capture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.logger import logger

_MSS_OK = False
_OCR_OK = False

try:
    import mss
    _MSS_OK = True
except ImportError:
    mss = None  # type: ignore

try:
    import easyocr
    _OCR_OK = True
except ImportError:
    easyocr = None  # type: ignore


@dataclass
class OcrSnapshot:
    food: Optional[int] = None
    wood: Optional[int] = None
    gold: Optional[int] = None
    stone: Optional[int] = None
    age_text: str = ""
    pop: Optional[int] = None
    raw_text: str = ""


class OcrWatcher:
    """
    Captures configured screen regions and runs OCR.
    Region coords are stored in settings (x, y, w, h).
    """

    def __init__(self):
        self._reader = None

    def is_available(self) -> bool:
        return _MSS_OK and _OCR_OK

    def _get_reader(self):
        if self._reader is None and _OCR_OK:
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._reader

    def capture_region(self, region: dict) -> Optional[bytes]:
        if not _MSS_OK:
            return None
        try:
            with mss.mss() as sct:
                shot = sct.grab(region)
                from PIL import Image
                import io
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.convert("L").save(buf, format="PNG")
                return buf.getvalue()
        except Exception as exc:
            logger.debug("OCR capture failed: %s", exc)
            return None

    def read_region(self, region: dict) -> OcrSnapshot:
        """Capture + OCR a screen region; returns parsed snapshot."""
        snap = OcrSnapshot()
        if not self.is_available():
            return snap

        try:
            with mss.mss() as sct:
                shot = sct.grab(region)
                from PIL import Image
                import numpy as np
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                arr = np.array(img.convert("L"))
                reader = self._get_reader()
                if not reader:
                    return snap
                results = reader.readtext(arr, detail=0)
                snap.raw_text = " ".join(results)

                for age in ("Dark", "Feudal", "Castle", "Imperial"):
                    if age.lower() in snap.raw_text.lower():
                        snap.age_text = age
                        break
        except Exception as exc:
            logger.warning("OCR read failed: %s", exc)

        return snap
