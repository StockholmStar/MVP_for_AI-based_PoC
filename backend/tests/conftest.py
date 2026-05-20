import os
import sys
import tempfile
from pathlib import Path


_TEST_DATA_DIR = tempfile.TemporaryDirectory(prefix="ai-workspace-test-")
os.environ["AI_WORKSPACE_DATA_DIR"] = _TEST_DATA_DIR.name

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
