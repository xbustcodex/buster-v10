from __future__ import annotations

"""
Runtime routing diagnostics for Buster.

Run from the project root:

    python -m pytest -s tests/test_runtime_routing.py
or:
    python tests/test_runtime_routing.py

This test does not start the Qt application. It inspects imports, source wiring,
module locations, and duplicate event subscriptions.
"""

import ast
import importlib
import importlib.util
import inspect
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUSTER_ROOT = PROJECT_ROOT / "buster"

TARGET_NAMES = {
    "SelfImprovementService",
    "StandardRepairWorkflowHandlers",
    "create_runtime_core",
    "legacy_runtime_core",
    "runtime_core",
    "chat_repair_bridge",
}


def iter_python_files() -> Iterable[Path]:
    yield from BUSTER_ROOT.rglob("*.py")


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def source_mentions() -> dict[str, list[tuple[int, str]]]:
    matches: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for path in iter_python_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for number, line in enumerate(lines, start=1):
            if any(name in line for name in TARGET_NAMES):
                matches[relative(path)].append((number, line.strip()))

    return dict(matches)


def import_edges() -> list[tuple[str, str, int]]:
    edges: list[tuple[str, str, int]] = []

    for path in iter_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("buster."):
                        edges.append((relative(path), alias.name, node.lineno))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("buster."):
                    imported = ", ".join(alias.name for alias in node.names)
                    edges.append(
                        (relative(path), f"{module} -> {imported}", node.lineno)
                    )

    return edges


def module_location(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return "<not found>"
    return str(spec.origin or spec.submodule_search_locations)


def print_routing_report() -> None:
    print("\n" + "=" * 78)
    print("BUSTER RUNTIME ROUTING REPORT")
    print("=" * 78)

    print("\n[1] Module resolution")
    modules = [
        "buster.runtime.core",
        "buster.autonomy.self_improvement_service",
        "buster.ui.v9.panels.self_improvement.self_improvement_service",
        "buster.ui.v9.chat_view",
        "buster.ui.v9.main_window",
    ]

    for name in modules:
        try:
            print(f"{name:<58} {module_location(name)}")
        except Exception as exc:
            print(f"{name:<58} ERROR: {exc}")

    print("\n[2] Runtime and self-improvement references")
    mentions = source_mentions()
    for path in sorted(mentions):
        print(f"\n{path}")
        for line_number, line in mentions[path]:
            print(f"  {line_number:>4}: {line}")

    print("\n[3] Relevant import edges")
    for source, target, line_number in sorted(import_edges()):
        if any(name in target for name in TARGET_NAMES) or "runtime" in target:
            print(f"  {source}:{line_number} -> {target}")

    print("\n[4] Loaded module duplicates")
    loaded_by_file: dict[str, list[str]] = defaultdict(list)
    for name, module in list(sys.modules.items()):
        file_name = getattr(module, "__file__", None)
        if file_name and "buster" in file_name.lower():
            loaded_by_file[str(Path(file_name).resolve())].append(name)

    duplicates = {
        file_name: names
        for file_name, names in loaded_by_file.items()
        if len(names) > 1
    }

    if not duplicates:
        print("  No duplicate loaded module files detected.")
    else:
        for file_name, names in duplicates.items():
            print(f"  {file_name}")
            for name in names:
                print(f"    - {name}")


def test_self_improvement_service_resolves_to_expected_module() -> None:
    """
    Verify that the unified repair service resolves from the new
    Self Improvement implementation and is exposed by the runtime as one
    singleton through all supported compatibility aliases.
    """
    expected_module_name = (
        "buster.ui.v9.panels.self_improvement."
        "self_improvement_service"
    )

    module = importlib.import_module(expected_module_name)
    service_class = getattr(module, "SelfImprovementService")

    service_module = inspect.getmodule(service_class)
    assert service_module is not None
    assert service_module.__name__ == expected_module_name

    source_file = Path(
        inspect.getsourcefile(service_class) or ""
    ).resolve()
    expected_root = (
        BUSTER_ROOT
        / "ui"
        / "v9"
        / "panels"
        / "self_improvement"
    ).resolve()

    assert expected_root in source_file.parents, (
        "SelfImprovementService is resolving from the wrong location:\n"
        f"  resolved: {source_file}\n"
        f"  expected under: {expected_root}"
    )

    runtime_module = importlib.import_module("buster.runtime.core")
    create_runtime_core = getattr(runtime_module, "create_runtime_core")
    runtime = create_runtime_core(str(PROJECT_ROOT))

    try:
        repair_service = getattr(runtime, "repair_service", None)
        service_alias = getattr(
            runtime,
            "self_improvement_service",
            None,
        )
        runtime_alias = getattr(
            runtime,
            "self_improvement_runtime",
            None,
        )
        autonomy_service = getattr(runtime, "self_improvement", None)

        assert repair_service is not None, (
            "BusterRuntimeCore did not initialize repair_service."
        )
        assert isinstance(repair_service, service_class)
        assert repair_service is service_alias
        assert repair_service is runtime_alias
        assert repair_service is not autonomy_service

    finally:
        stop = getattr(runtime, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass


def test_chat_view_does_not_directly_construct_old_runtime() -> None:
    chat_view_path = BUSTER_ROOT / "ui" / "v9" / "chat_view.py"
    source = chat_view_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source)

    forbidden_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name in {"create_runtime_core", "SelfImprovementService"}:
                forbidden_calls.append((name, node.lineno))

    assert not forbidden_calls, (
        "chat_view.py constructs runtime/service objects directly instead of "
        "receiving them from the unified runtime:\n"
        + "\n".join(
            f"  {name}() at line {line}"
            for name, line in forbidden_calls
        )
    )


def test_main_window_passes_one_runtime_to_chat() -> None:
    main_window_path = BUSTER_ROOT / "ui" / "v9" / "main_window.py"
    source = main_window_path.read_text(encoding="utf-8", errors="replace")

    assert "class V9MainWindow" in source, (
        "main_window.py no longer contains V9MainWindow. Restore the file "
        "before testing runtime routing."
    )

    tree = ast.parse(source)
    chat_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name == "ChatView":
                chat_calls.append(node)

    assert len(chat_calls) == 1, (
        f"Expected exactly one ChatView construction, found {len(chat_calls)}."
    )

    call = chat_calls[0]
    runtime_keywords = {
        keyword.arg: ast.unparse(keyword.value)
        for keyword in call.keywords
        if keyword.arg in {"runtime_core", "legacy_runtime_core"}
    }

    assert runtime_keywords, (
        "ChatView is not explicitly receiving a runtime object."
    )

    values = set(runtime_keywords.values())
    assert len(values) == 1, (
        "ChatView receives more than one runtime reference:\n"
        f"  {runtime_keywords}"
    )


def find_duplicate_callbacks(event_bus: object) -> dict[str, list[str]]:
    """
    Best-effort detector for common EventBus storage layouts.

    Supports dictionaries such as:
        _subscribers[event_name] = [callback, callback]
        handlers[event_name] = [...]
        subscriptions[event_name] = [...]
    """
    duplicate_report: dict[str, list[str]] = {}

    for attr_name in (
        "_subscribers",
        "subscribers",
        "_handlers",
        "handlers",
        "_subscriptions",
        "subscriptions",
    ):
        registry = getattr(event_bus, attr_name, None)
        if not isinstance(registry, dict):
            continue

        for event_name, callbacks in registry.items():
            if not isinstance(callbacks, (list, tuple, set)):
                continue

            identities = []
            labels = []

            for callback in callbacks:
                owner = getattr(callback, "__self__", None)
                function = getattr(callback, "__func__", callback)
                identity = (id(owner), id(function))
                identities.append(identity)

                owner_name = (
                    owner.__class__.__name__ if owner is not None else "<module>"
                )
                function_name = getattr(function, "__qualname__", repr(function))
                labels.append(f"{owner_name}.{function_name}")

            counts = Counter(identities)
            duplicates = [
                labels[index]
                for index, identity in enumerate(identities)
                if counts[identity] > 1
            ]

            if duplicates:
                duplicate_report[f"{attr_name}:{event_name}"] = duplicates

    return duplicate_report


def test_runtime_has_no_duplicate_event_handlers() -> None:
    """
    Creates the runtime but does not start the UI.

    Buster has used several names for its routing component over time. Resolve
    the component exposed by the current runtime instead of requiring the
    legacy event_bus attribute.
    """
    runtime_module = importlib.import_module("buster.runtime.core")
    create_runtime_core = getattr(runtime_module, "create_runtime_core")
    runtime = create_runtime_core(str(PROJECT_ROOT))

    try:
        routing_component = None
        resolved_attribute = None

        for attribute in (
            "event_bus",
            "event_router",
            "dispatcher",
            "router",
        ):
            candidate = getattr(runtime, attribute, None)
            if candidate is not None:
                routing_component = candidate
                resolved_attribute = attribute
                break

        if routing_component is None:
            kernel = getattr(runtime, "kernel", None)
            if kernel is not None:
                for attribute in (
                    "event_bus",
                    "event_router",
                    "dispatcher",
                    "router",
                ):
                    candidate = getattr(kernel, attribute, None)
                    if candidate is not None:
                        routing_component = candidate
                        resolved_attribute = f"kernel.{attribute}"
                        break

        assert routing_component is not None, (
            "Unified runtime exposes no recognized routing component. "
            "Checked event_bus, event_router, dispatcher, router, and the "
            "same attributes under runtime.kernel."
        )

        duplicates = find_duplicate_callbacks(routing_component)
        assert not duplicates, (
            "Duplicate event handlers detected on "
            f"{resolved_attribute}. These can cause repair loops:\n"
            + "\n".join(
                f"  {event}: {callbacks}"
                for event, callbacks in duplicates.items()
            )
        )

    finally:
        stop = getattr(runtime, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:
                pass


def main() -> int:
    print_routing_report()

    tests = [
        test_self_improvement_service_resolves_to_expected_module,
        test_chat_view_does_not_directly_construct_old_runtime,
        test_main_window_passes_one_runtime_to_chat,
        test_runtime_has_no_duplicate_event_handlers,
    ]

    failures = 0

    for test in tests:
        try:
            test()
            print(f"\nPASS: {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"\nFAIL: {test.__name__}")
            print(f"  {exc}")

    print("\n" + "=" * 78)
    print(f"Completed with {failures} failure(s).")
    print("=" * 78)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
