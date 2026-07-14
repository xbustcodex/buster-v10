from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any


class ComponentType(Enum):
    CORE = "core"
    UI = "ui"
    MEMORY = "memory"
    VOICE = "voice"
    VISION = "vision"
    AGENTS = "agents"
    PLUGINS = "plugins"
    THEMES = "themes"
    ASSETS = "assets"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"


class UpdateStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class UpgradePlan:
    from_version: str
    to_version: str
    operations: List[Dict[str, Any]]
    files_to_update: int
    files_to_delete: int
    files_to_create: int
    disk_required: int
    rollback_available: bool
    components_affected: List[str]


@dataclass
class HealthReport:
    overall_score: float
    runtime_score: float
    imports_score: float
    config_score: float
    plugins_score: float
    database_score: float
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    timestamp: str
