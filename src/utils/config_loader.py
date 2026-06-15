import json
from pathlib import Path


def load_config(config_path: str) -> dict:
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if "laptop_id" not in config:
        raise ValueError("Config must contain laptop_id.")

    if "bands" not in config or not isinstance(config["bands"], list):
        raise ValueError("Config must contain a bands list.")

    for band in config["bands"]:
        required = ["participant_id", "device_identifier", "stream_name"]
        for key in required:
            if key not in band:
                raise ValueError(f"Band config missing required key: {key}")

    return config
