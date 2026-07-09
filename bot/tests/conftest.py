import sys
from pathlib import Path

# Allow running tests without installing the packages: add the bot and
# shared db packages' src/ directories to sys.path directly.
_BOT_SRC = Path(__file__).resolve().parent.parent / "src"
_DB_SRC = Path(__file__).resolve().parent.parent.parent / "db" / "src"

for path in (_BOT_SRC, _DB_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
