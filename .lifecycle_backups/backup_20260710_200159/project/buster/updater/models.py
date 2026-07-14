from dataclasses import dataclass

@dataclass
class UpdateInfo:
    checked: bool
    available: bool
    current_version: str
    latest_version: str = ""
    release_url: str = ""
    release_name: str = ""
    error: str = ""
