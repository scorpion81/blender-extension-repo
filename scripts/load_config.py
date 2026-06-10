import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
CONFIG = ROOT / "registry.yml"

def load_config():
    with open(CONFIG, "r") as f:
        return yaml.safe_load(f)

def validate(cfg):
    for name, pkg in cfg["packages"].items():
        if "repo" not in pkg:
            raise ValueError(f"{name} missing repo")
        if "ref" not in pkg:
            raise ValueError(f"{name} missing ref")

def get_package(cfg, name):
    return cfg["packages"][name]

if __name__ == "__main__":
    cfg = load_config()
    validate(cfg)

    # CLI usage: python load_config.py pkg-a repo
    import sys

    if len(sys.argv) >= 3:
        pkg = sys.argv[1]
        key = sys.argv[2]

        print(cfg["packages"][pkg][key])
