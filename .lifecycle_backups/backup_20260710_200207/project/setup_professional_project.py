from pathlib import Path

ROOT = Path.cwd()

FILES = {
    "docs/architecture/RUNTIME_API.md": (
        "# Buster Runtime API\n\n"
        "Stable interfaces:\n\n"
        "```python\n"
        "runtime.events\n"
        "runtime.jobs\n"
        "runtime.services\n"
        "runtime.registry\n"
        "runtime.blackboard\n"
        "runtime.agent_memory\n"
        "runtime.orchestrator\n"
        "runtime.devtools\n"
        "```\n"
    ),

    "docs/architecture/PLUGIN_API.md": (
        "# Plugin API\n\n"
        "```python\n"
        "class ExamplePlugin:\n"
        "    name = 'example'\n"
        "    version = '1.0.0'\n\n"
        "    def register(self, runtime):\n"
        "        runtime.services.register('example', self)\n"
        "```\n"
    ),

    "docs/architecture/ROADMAP.md": (
        "# Buster Roadmap\n\n"
        "## Complete\n"
        "- Runtime Core\n"
        "- Runtime Registry\n"
        "- Job Manager\n"
        "- Agent Framework\n"
        "- Runtime Console\n\n"
        "## Next\n"
        "- Mission Control 3.0\n"
        "- Workflow Graph\n"
        "- Plugin Manager\n"
        "- Voice Runtime\n"
        "- Vision Runtime\n"
    ),

    "CONTRIBUTING.md": (
        "# Contributing\n\n"
        "Create feature branches.\n\n"
        "Run:\n\n"
        "```\n"
        "pytest\n"
        "python run_lifecycle.py health\n"
        "```\n"
    ),

    ".github/pull_request_template.md": (
        "## Summary\n\n"
        "Describe the change.\n\n"
        "### Checklist\n"
        "- [ ] Tests pass\n"
        "- [ ] Lifecycle health passes\n"
        "- [ ] Runtime state not committed\n"
    ),

    ".github/ISSUE_TEMPLATE/bug_report.md": (
        "---\n"
        "name: Bug Report\n"
        "about: Report a bug\n"
        "---\n\n"
        "## Description\n"
    ),

    ".github/ISSUE_TEMPLATE/feature_request.md": (
        "---\n"
        "name: Feature Request\n"
        "about: Suggest a feature\n"
        "---\n\n"
        "## Feature\n"
    ),

    "scripts/new_feature_branch.bat": (
        "@echo off\n"
        "if \"%1\"==\"\" (\n"
        " echo Usage: new_feature_branch.bat feature-name\n"
        " exit /b 1\n"
        ")\n\n"
        "git checkout main\n"
        "git pull\n"
        "git checkout -b feature/%1\n"
    ),

    "scripts/pre_commit_check.bat": (
        "@echo off\n"
        "python run_lifecycle.py health\n"
        "pytest\n"
    ),
}

for relative_path, content in FILES.items():
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Created: {relative_path}")

print("\nProfessional project structure created successfully.")