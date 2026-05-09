"""Flashcard Guru Remote — Anki desktop add-on entry point.

This module is loaded by Anki at startup. It registers gui_hooks that spin up
the WebSocket server when a profile is opened and tear it down on close.

Tests in this repo run without aqt installed; we therefore guard the Anki
import so test discovery stays clean.
"""
from __future__ import annotations

import os
import sys

# Make vendored runtime deps importable. The vendor/ dir is populated by
# scripts/vendor_deps.sh and ships inside the .ankiaddon bundle.
_VENDOR_DIR = os.path.join(os.path.dirname(__file__), "vendor")
if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

try:
    import aqt  # noqa: F401
except ImportError:
    # Running outside Anki (e.g., pytest). Submodules import lazily.
    pass
else:
    from . import _anki_entry  # noqa: F401  — registers gui_hooks
