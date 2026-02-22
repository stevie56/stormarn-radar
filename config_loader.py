"""
config_loader.py – Lädt die YAML-Konfiguration einmalig
"""
from pathlib import Path
import yaml

_CONFIG = None


def load_config(path: str = None) -> dict:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    config_path = Path(path) if path else Path(__file__).parent / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        _CONFIG = yaml.safe_load(f)
    return _CONFIG


def get(key: str, default=None):
    """Zugriff auf verschachtelte Keys mit Punkt-Notation z.B. 'radar.topic'"""
    cfg = load_config()
    keys = key.split(".")
    val = cfg
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val
