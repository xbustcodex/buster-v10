from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    app_name: str = "Buster Companion"
    version: str = "8.0"
    wake_word: str = "hey buster"

    data_dir: Path = Path("data")
    logs_dir: Path = Path("logs")
    screenshots_dir: Path = Path("screenshots")
    memory_db: Path = Path("data/buster_memory.db")
    app_cache_file: Path = Path("data/apps_cache.json")
    ai_config_file: Path = Path("data/ai_provider_config.json")

    always_on_top: bool = True
    main_width: int = 1320
    main_height: int = 900
    compact_width: int = 420
    compact_height: int = 620
