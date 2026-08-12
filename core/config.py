import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
NAMES_FILE = os.path.join(BASE_DIR, "names.txt")

DEFAULT_CONFIG = {
    "api_id": 0,
    "api_hash": "",
    "phone": "",
    "interval_hours": 6,
    "jitter_minutes": 30,
    "names": [],
}


def load_names_from_file() -> list:
    """Читает имена из names.txt если файл существует."""
    if not os.path.exists(NAMES_FILE):
        return []
    names = []
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                names.append(line)
    return names


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    # Сначала загружаем имена из файла как дефолт
    file_names = load_names_from_file()
    if file_names:
        config["names"] = file_names
    # Потом перезаписываем из config.json если есть
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Если в config.json есть непустой список — он приоритетнее
            if saved.get("names"):
                config.update(saved)
            else:
                saved.pop("names", None)
                config.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
