import os
import json
import platform
import pathlib
from typing import Any, Dict, List, Set

def _parse_size(size_str: str) -> int:
    """Parse human-readable size strings like '10MB', '500KB' into bytes."""
    s = size_str.strip().upper()
    if s.endswith("KB"):
        return int(s[:-2]) * 1024
    if s.endswith("MB"):
        return int(s[:-2]) * 1024 ** 2
    if s.endswith("GB"):
        return int(s[:-2]) * 1024 ** 3
    return int(s)

def _load_json_config() -> Dict[str, Any]:
    """Load OS-specific JSON config with ironclad absolute paths."""
    # Force absolute lookup relative to this file's directory
    current_file_path = pathlib.Path(__file__).parent.resolve()
    base = current_file_path.parent.parent / "config"
    
    os_name = platform.system().lower()
    cfg_file = base / f"{os_name}.json"
    
    if not cfg_file.exists():
        cfg_file = base / "default.json"
        
    if not cfg_file.exists():
        # Safeguard fallback if config directory is not found
        return {"allowed_paths": ["~/Desktop", "~/Downloads"], "max_file_size": "20MB", "allowed_extensions": []}
        
    try:
        with cfg_file.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _load_env_config() -> Dict[str, Any]:
    """Override config values via environment variables."""
    env_cfg: Dict[str, Any] = {}
    if (paths := os.environ.get("FILESYSTEM_ALLOWED_PATHS")):
        env_cfg["allowed_paths"] = paths.split(os.pathsep)
    if (size := os.environ.get("FILESYSTEM_MAX_FILE_SIZE")):
        env_cfg["max_file_size"] = size
    if (exts := os.environ.get("FILESYSTEM_ALLOWED_EXTENSIONS")):
        env_cfg["allowed_extensions"] = [e.strip() for e in exts.split(",")]
    return env_cfg

def load_config() -> Dict[str, Any]:
    """Merge JSON and environment configs and normalize types."""
    cfg = _load_json_config()
    env = _load_env_config()
    
    paths: List[str] = env.get("allowed_paths") or cfg.get("allowed_paths") or []
    cfg["allowed_paths"] = [pathlib.Path(p).expanduser().resolve() for p in paths]
    
    size_str = env.get("max_file_size") or cfg.get("max_file_size", "10MB")
    cfg["max_file_size"] = _parse_size(size_str)
    
    exts = env.get("allowed_extensions") or cfg.get("allowed_extensions") or []
    cfg["allowed_extensions"] = set(e.lower() for e in exts)
    return cfg