import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DICT = ROOT / "src-dict"

# so `import inflection` (used by check-syntax.py and dictlogic) resolves
sys.path.insert(0, str(SRC_DICT))
# so `import editor...` resolves when running pytest from anywhere
sys.path.insert(0, str(ROOT))
