"""
Buster v3.5 Learning + Plugin OS Patch
Adds:
- buster.learning package
- plugin registry / loader / marketplace helpers
- strategy planner
- JSON data stores

Run from your project root:
    python apply_v3_5_learning_plugin_os.py
Then test:
    python test_v3_5_learning_plugin_os.py
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent


def write_file(relative_path: str, content: str) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")
    print(f"[WRITE] {relative_path}")


def write_json_if_missing(relative_path: str, default_data) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default_data, indent=2), encoding="utf-8")
        print(f"[CREATE] {relative_path}")
    else:
        print(f"[KEEP] {relative_path}")


FILES = {
    "buster/learning/__init__.py": '''
        """Buster Learning Engine.

        This package lets Buster remember what worked, what failed,
        and which strategies should be reused on future projects.
        """

        from .engine import LearningEngine
        from .experience import ExperienceRecord
        from .patterns import DesignPatternStore
        from .strategies import BuildStrategyStore

        __all__ = [
            "LearningEngine",
            "ExperienceRecord",
            "DesignPatternStore",
            "BuildStrategyStore",
        ]
    ''',
    "buster/learning/experience.py": '''
        from __future__ import annotations

        from dataclasses import dataclass, field, asdict
        from datetime import datetime
        from typing import Any, Dict, List, Optional
        import uuid


        @dataclass
        class ExperienceRecord:
            """One reusable lesson from a Buster job."""

            task: str
            project: str = "default"
            outcome: str = "unknown"  # success, failure, partial
            strategy: str = "general"
            what_worked: List[str] = field(default_factory=list)
            what_failed: List[str] = field(default_factory=list)
            fixes: List[str] = field(default_factory=list)
            reusable_patterns: List[str] = field(default_factory=list)
            tags: List[str] = field(default_factory=list)
            score: float = 0.0
            metadata: Dict[str, Any] = field(default_factory=dict)
            created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
            id: str = field(default_factory=lambda: str(uuid.uuid4()))

            def to_dict(self) -> Dict[str, Any]:
                return asdict(self)

            @classmethod
            def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
                known = {field.name for field in cls.__dataclass_fields__.values()}
                cleaned = {key: value for key, value in data.items() if key in known}
                return cls(**cleaned)
    ''',
    "buster/learning/patterns.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional


        class DesignPatternStore:
            """Stores reusable project and code design patterns."""

            def __init__(self, path: str | Path = "data/design_patterns.json") -> None:
                self.path = Path(path)
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.patterns: List[Dict[str, Any]] = self._load()

            def _load(self) -> List[Dict[str, Any]]:
                if not self.path.exists():
                    return []
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                    return data if isinstance(data, list) else data.get("patterns", [])
                except Exception:
                    return []

            def save(self) -> None:
                self.path.write_text(json.dumps(self.patterns, indent=2), encoding="utf-8")

            def add_pattern(
                self,
                name: str,
                description: str,
                project_type: str = "general",
                tags: Optional[List[str]] = None,
                source: str = "learning",
            ) -> Dict[str, Any]:
                pattern = {
                    "name": name,
                    "description": description,
                    "project_type": project_type,
                    "tags": tags or [],
                    "source": source,
                    "uses": 0,
                }
                self.patterns.append(pattern)
                self.save()
                return pattern

            def search(self, query: str = "", project_type: Optional[str] = None) -> List[Dict[str, Any]]:
                query_l = query.lower().strip()
                results = []
                for pattern in self.patterns:
                    blob = " ".join([
                        pattern.get("name", ""),
                        pattern.get("description", ""),
                        " ".join(pattern.get("tags", [])),
                        pattern.get("project_type", ""),
                    ]).lower()
                    if project_type and pattern.get("project_type") not in (project_type, "general"):
                        continue
                    if not query_l or query_l in blob:
                        results.append(pattern)
                return results
    ''',
    "buster/learning/strategies.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional


        class BuildStrategyStore:
            """Tracks build strategies and recommends the best one for a request."""

            def __init__(self, path: str | Path = "data/build_strategies.json") -> None:
                self.path = Path(path)
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.strategies: List[Dict[str, Any]] = self._load()
                if not self.strategies:
                    self._seed_defaults()

            def _load(self) -> List[Dict[str, Any]]:
                if not self.path.exists():
                    return []
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                    return data if isinstance(data, list) else data.get("strategies", [])
                except Exception:
                    return []

            def save(self) -> None:
                self.path.write_text(json.dumps(self.strategies, indent=2), encoding="utf-8")

            def _seed_defaults(self) -> None:
                self.strategies = [
                    {
                        "name": "plan_build_test_fix_verify",
                        "description": "Plan first, build files, run tests, fix errors, verify result.",
                        "project_types": ["python", "desktop", "general"],
                        "successes": 0,
                        "failures": 0,
                        "score": 0.75,
                    },
                    {
                        "name": "small_incremental_patch",
                        "description": "Apply a small safe patch, then test immediately.",
                        "project_types": ["existing_project", "bugfix", "general"],
                        "successes": 0,
                        "failures": 0,
                        "score": 0.70,
                    },
                    {
                        "name": "modular_plugin_expansion",
                        "description": "Add new capability as a module or plugin instead of growing main.py.",
                        "project_types": ["buster", "plugin", "ai_os"],
                        "successes": 0,
                        "failures": 0,
                        "score": 0.85,
                    },
                ]
                self.save()

            def record_result(self, name: str, success: bool) -> None:
                strategy = self.get(name)
                if strategy is None:
                    strategy = {
                        "name": name,
                        "description": "Learned strategy",
                        "project_types": ["general"],
                        "successes": 0,
                        "failures": 0,
                        "score": 0.50,
                    }
                    self.strategies.append(strategy)

                if success:
                    strategy["successes"] = strategy.get("successes", 0) + 1
                else:
                    strategy["failures"] = strategy.get("failures", 0) + 1

                total = strategy.get("successes", 0) + strategy.get("failures", 0)
                if total:
                    strategy["score"] = round(strategy.get("successes", 0) / total, 3)
                self.save()

            def get(self, name: str) -> Optional[Dict[str, Any]]:
                for strategy in self.strategies:
                    if strategy.get("name") == name:
                        return strategy
                return None

            def recommend(self, project_type: str = "general", query: str = "") -> Dict[str, Any]:
                query_l = query.lower()
                candidates = []
                for strategy in self.strategies:
                    types = strategy.get("project_types", [])
                    blob = (strategy.get("name", "") + " " + strategy.get("description", "")).lower()
                    type_match = project_type in types or "general" in types
                    text_bonus = 0.1 if query_l and query_l in blob else 0.0
                    if type_match or text_bonus:
                        score = float(strategy.get("score", 0.0)) + text_bonus
                        candidates.append((score, strategy))
                if not candidates:
                    return self.strategies[0]
                return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    ''',
    "buster/learning/engine.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional

        from .experience import ExperienceRecord
        from .patterns import DesignPatternStore
        from .strategies import BuildStrategyStore


        class LearningEngine:
            """Central learning loop for Buster AI OS.

            Records completed work, extracts reusable patterns, updates strategy scores,
            and recommends better approaches for the next project.
            """

            def __init__(
                self,
                memory_path: str | Path = "data/learning_memory.json",
                strategies_path: str | Path = "data/build_strategies.json",
                patterns_path: str | Path = "data/design_patterns.json",
            ) -> None:
                self.memory_path = Path(memory_path)
                self.memory_path.parent.mkdir(parents=True, exist_ok=True)
                self.strategy_store = BuildStrategyStore(strategies_path)
                self.pattern_store = DesignPatternStore(patterns_path)
                self.records: List[ExperienceRecord] = self._load_records()

            def _load_records(self) -> List[ExperienceRecord]:
                if not self.memory_path.exists():
                    return []
                try:
                    raw = json.loads(self.memory_path.read_text(encoding="utf-8"))
                    items = raw if isinstance(raw, list) else raw.get("records", [])
                    return [ExperienceRecord.from_dict(item) for item in items]
                except Exception:
                    return []

            def save(self) -> None:
                self.memory_path.write_text(
                    json.dumps([record.to_dict() for record in self.records], indent=2),
                    encoding="utf-8",
                )

            def record_experience(self, record: ExperienceRecord | Dict[str, Any]) -> ExperienceRecord:
                if isinstance(record, dict):
                    record = ExperienceRecord.from_dict(record)
                self.records.append(record)
                self.strategy_store.record_result(record.strategy, record.outcome == "success")

                for pattern in record.reusable_patterns:
                    self.pattern_store.add_pattern(
                        name=pattern[:80],
                        description=pattern,
                        project_type=record.project,
                        tags=record.tags,
                        source=record.id,
                    )

                self.save()
                return record

            def learn_from_job(
                self,
                task: str,
                project: str,
                success: bool,
                strategy: str,
                what_worked: Optional[List[str]] = None,
                what_failed: Optional[List[str]] = None,
                fixes: Optional[List[str]] = None,
                reusable_patterns: Optional[List[str]] = None,
                tags: Optional[List[str]] = None,
                metadata: Optional[Dict[str, Any]] = None,
            ) -> ExperienceRecord:
                record = ExperienceRecord(
                    task=task,
                    project=project,
                    outcome="success" if success else "failure",
                    strategy=strategy,
                    what_worked=what_worked or [],
                    what_failed=what_failed or [],
                    fixes=fixes or [],
                    reusable_patterns=reusable_patterns or [],
                    tags=tags or [],
                    score=1.0 if success else 0.0,
                    metadata=metadata or {},
                )
                return self.record_experience(record)

            def recommend_strategy(self, project_type: str = "general", request: str = "") -> Dict[str, Any]:
                strategy = self.strategy_store.recommend(project_type, request)
                patterns = self.pattern_store.search(request, project_type=project_type)[:5]
                similar = self.search_experience(request, project=project_type)[:5]
                return {
                    "strategy": strategy,
                    "patterns": patterns,
                    "similar_experiences": [item.to_dict() for item in similar],
                }

            def search_experience(self, query: str = "", project: Optional[str] = None) -> List[ExperienceRecord]:
                query_l = query.lower().strip()
                results: List[ExperienceRecord] = []
                for record in self.records:
                    blob = " ".join([
                        record.task,
                        record.project,
                        record.strategy,
                        " ".join(record.what_worked),
                        " ".join(record.what_failed),
                        " ".join(record.fixes),
                        " ".join(record.reusable_patterns),
                        " ".join(record.tags),
                    ]).lower()
                    if project and record.project not in (project, "general"):
                        continue
                    if not query_l or query_l in blob:
                        results.append(record)
                return list(reversed(results))

            def summary(self) -> Dict[str, Any]:
                successes = sum(1 for record in self.records if record.outcome == "success")
                failures = sum(1 for record in self.records if record.outcome == "failure")
                return {
                    "records": len(self.records),
                    "successes": successes,
                    "failures": failures,
                    "strategies": len(self.strategy_store.strategies),
                    "patterns": len(self.pattern_store.patterns),
                }
    ''',
    "buster/plugins/registry.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional


        class PluginRegistry:
            """Persistent registry for installed Buster capabilities."""

            def __init__(self, path: str | Path = "data/plugin_registry.json") -> None:
                self.path = Path(path)
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.plugins: Dict[str, Dict[str, Any]] = self._load()

            def _load(self) -> Dict[str, Dict[str, Any]]:
                if not self.path.exists():
                    return {}
                try:
                    data = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "plugins" in data:
                        return data["plugins"]
                    return data if isinstance(data, dict) else {}
                except Exception:
                    return {}

            def save(self) -> None:
                self.path.write_text(json.dumps({"plugins": self.plugins}, indent=2), encoding="utf-8")

            def register(
                self,
                name: str,
                module: str,
                capabilities: Optional[List[str]] = None,
                enabled: bool = True,
                metadata: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                self.plugins[name] = {
                    "name": name,
                    "module": module,
                    "capabilities": capabilities or [],
                    "enabled": enabled,
                    "metadata": metadata or {},
                }
                self.save()
                return self.plugins[name]

            def unregister(self, name: str) -> bool:
                existed = name in self.plugins
                self.plugins.pop(name, None)
                self.save()
                return existed

            def enable(self, name: str, enabled: bool = True) -> None:
                if name in self.plugins:
                    self.plugins[name]["enabled"] = enabled
                    self.save()

            def list_plugins(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
                items = list(self.plugins.values())
                if enabled_only:
                    items = [item for item in items if item.get("enabled", True)]
                return items

            def find_by_capability(self, capability: str) -> List[Dict[str, Any]]:
                capability_l = capability.lower()
                return [
                    plugin for plugin in self.list_plugins(enabled_only=True)
                    if any(capability_l in cap.lower() for cap in plugin.get("capabilities", []))
                ]
    ''',
    "buster/plugins/loader.py": '''
        from __future__ import annotations

        import importlib
        from typing import Any, Dict, List

        from .registry import PluginRegistry


        class PluginLoader:
            """Loads enabled plugins without bloating Buster core."""

            def __init__(self, registry: PluginRegistry | None = None) -> None:
                self.registry = registry or PluginRegistry()
                self.loaded: Dict[str, Any] = {}

            def load_enabled(self) -> Dict[str, Any]:
                for plugin in self.registry.list_plugins(enabled_only=True):
                    self.load_plugin(plugin["name"])
                return self.loaded

            def load_plugin(self, name: str) -> Any:
                plugin = self.registry.plugins.get(name)
                if not plugin:
                    raise KeyError(f"Plugin not registered: {name}")
                module_name = plugin["module"]
                module = importlib.import_module(module_name)

                if hasattr(module, "create_plugin"):
                    instance = module.create_plugin()
                elif hasattr(module, "Plugin"):
                    instance = module.Plugin()
                else:
                    instance = module

                self.loaded[name] = instance
                return instance

            def commands(self) -> Dict[str, Any]:
                commands: Dict[str, Any] = {}
                for name, plugin in self.loaded.items():
                    if hasattr(plugin, "commands"):
                        value = plugin.commands
                        commands[name] = value() if callable(value) else value
                return commands
    ''',
    "buster/plugins/marketplace.py": '''
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any, Dict, List, Optional

        from .registry import PluginRegistry


        class PluginMarketplace:
            """Simple local marketplace index for future installable capabilities."""

            def __init__(self, index_path: str | Path = "data/plugin_marketplace.json") -> None:
                self.index_path = Path(index_path)
                self.index_path.parent.mkdir(parents=True, exist_ok=True)
                self.items: List[Dict[str, Any]] = self._load()
                if not self.items:
                    self._seed_defaults()

            def _load(self) -> List[Dict[str, Any]]:
                if not self.index_path.exists():
                    return []
                try:
                    data = json.loads(self.index_path.read_text(encoding="utf-8"))
                    return data if isinstance(data, list) else data.get("plugins", [])
                except Exception:
                    return []

            def save(self) -> None:
                self.index_path.write_text(json.dumps({"plugins": self.items}, indent=2), encoding="utf-8")

            def _seed_defaults(self) -> None:
                self.items = [
                    {
                        "name": "android",
                        "module": "buster.plugins.builtin.android_plugin",
                        "description": "Android Studio, Gradle, APK, Logcat and emulator workflows.",
                        "capabilities": ["android", "gradle", "apk", "logcat"],
                    },
                    {
                        "name": "esp32",
                        "module": "buster.plugins.builtin.esp32_plugin",
                        "description": "ESP32, Arduino, firmware and serial workflows.",
                        "capabilities": ["esp32", "arduino", "firmware", "serial"],
                    },
                    {
                        "name": "github",
                        "module": "buster.plugins.builtin.github_plugin",
                        "description": "GitHub repository, issue and release workflows.",
                        "capabilities": ["git", "github", "release", "repo"],
                    },
                ]
                self.save()

            def search(self, query: str = "") -> List[Dict[str, Any]]:
                query_l = query.lower().strip()
                if not query_l:
                    return self.items
                return [
                    item for item in self.items
                    if query_l in json.dumps(item).lower()
                ]

            def install(self, name: str, registry: Optional[PluginRegistry] = None) -> Dict[str, Any]:
                registry = registry or PluginRegistry()
                for item in self.items:
                    if item.get("name") == name:
                        return registry.register(
                            name=item["name"],
                            module=item["module"],
                            capabilities=item.get("capabilities", []),
                            metadata={"description": item.get("description", ""), "source": "marketplace"},
                        )
                raise KeyError(f"Marketplace plugin not found: {name}")
    ''',
    "buster/brain/planner/strategy_planner.py": '''
        from __future__ import annotations

        from typing import Any, Dict

        from buster.learning import LearningEngine
        from buster.plugins.registry import PluginRegistry


        class StrategyPlanner:
            """Planner bridge between Buster Brain, Learning Engine and Plugins."""

            def __init__(self, learning: LearningEngine | None = None, registry: PluginRegistry | None = None) -> None:
                self.learning = learning or LearningEngine()
                self.registry = registry or PluginRegistry()

            def plan(self, request: str, project_type: str = "general") -> Dict[str, Any]:
                recommendation = self.learning.recommend_strategy(project_type=project_type, request=request)
                plugins = self.registry.find_by_capability(project_type)

                steps = [
                    "Understand user request",
                    f"Use strategy: {recommendation['strategy'].get('name')}",
                    "Assign agent team",
                    "Execute build/test/fix/verify loop",
                    "Record outcome in Learning Engine",
                ]
                if plugins:
                    steps.insert(2, "Load matching plugins")

                return {
                    "request": request,
                    "project_type": project_type,
                    "recommended_strategy": recommendation["strategy"],
                    "reusable_patterns": recommendation["patterns"],
                    "similar_experiences": recommendation["similar_experiences"],
                    "plugins": plugins,
                    "steps": steps,
                }
    ''',
}


def main() -> None:
    print("=== Applying Buster v3.5 Learning + Plugin OS Patch ===")
    for relative_path, content in FILES.items():
        write_file(relative_path, content)

    write_json_if_missing("data/learning_memory.json", [])
    write_json_if_missing("data/build_strategies.json", {"strategies": []})
    write_json_if_missing("data/design_patterns.json", [])
    write_json_if_missing("data/plugin_registry.json", {"plugins": {}})
    write_json_if_missing("data/plugin_marketplace.json", {"plugins": []})

    print("\nSUCCESS: Buster v3.5 Learning + Plugin OS installed.")
    print("Next: python test_v3_5_learning_plugin_os.py")


if __name__ == "__main__":
    main()
