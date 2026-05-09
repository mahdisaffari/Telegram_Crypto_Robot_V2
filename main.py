"""Run the Telegram bot (adds `src` to PYTHONPATH)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from arbitrage_bot.runner import main as run_main


if __name__ == "__main__":
    run_main()
