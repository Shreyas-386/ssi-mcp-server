import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Alerts"))
sys.path.insert(0, str(ROOT / "layers" / "common"))
sys.path.insert(0, str(ROOT / "layers" / "common_stg"))

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
