import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "api_id": 0,
    "api_hash": "",
    "phone": "",
    "interval_hours": 6,
    "jitter_minutes": 30,
    "names": ["Ink", "Echo", "Wisp", "Void", "Haze", "Blur", "Fade", "Mist", "Ash", "Dust", "Smoke", "Shade", "Ghost", "Hush", "Faint", "Murk", "Grain", "Trace", "Mark", "Stain", "Smudge", "Fuzz", "Static", "Noise", "Hum", "Whisper", "Flicker", "Glitch", "Pixel", "Mono", "Film", "Tape", "Paper", "Note", "Tone", "Coda", "Lore", "Myth", "Moss", "Fern", "Twig", "Thorn", "Stone", "Brick", "Rust", "Coal", "Cinder", "Moth", "Crow", "Wren", "Owl", "Fox", "Fawn", "Nox", "Vex", "Zed", "Rift", "Loop", "Fold", "Thread", "Edge", "Dot", "Dash", "Zero", "None", "Null", "Blank", "Lost", "Empty", "Unknown", "Nobody", "Nowhere", "Away", "Idle", "Offline", "Quiet", "Still", "Cold", "Soft", "Dull", "Odd", "Weird", "Plain", "Simple", "Random", "Normal", "Basic", "Casual", "Maybe", "Almost", "Later", "Again", "Never", "Nothing", "Something", "Whatever", "Anyway"],
}


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)