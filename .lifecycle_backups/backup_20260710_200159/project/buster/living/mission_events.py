from __future__ import annotations

class MissionEventType:
    PLANNER_CREATED_MISSION = "planner.created_mission"
    REPOSITORY_INDEXED = "repository.indexed"
    BUILDER_GENERATED_CODE = "builder.generated_code"
    TESTER_FOUND_FAILURE = "tester.found_failure"
    TESTER_PASSED = "tester.passed"
    FIXER_REPAIRED_ISSUE = "fixer.repaired_issue"
    REVIEWER_REVIEWED = "reviewer.reviewed"
    VERIFIER_APPROVED_BUILD = "verifier.approved_build"
    LEARNING_RECORDED_PATTERN = "learning.recorded_pattern"
    EXPERIENCE_UPDATED_SKILL = "experience.updated_skill"
    PLUGIN_LOADED = "plugin.loaded"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"

EVENT_LABELS = {
    MissionEventType.PLANNER_CREATED_MISSION: ("Planner", "created mission"),
    MissionEventType.REPOSITORY_INDEXED: ("Repository", "indexed project"),
    MissionEventType.BUILDER_GENERATED_CODE: ("Builder", "generated code"),
    MissionEventType.TESTER_FOUND_FAILURE: ("Tester", "found failure"),
    MissionEventType.TESTER_PASSED: ("Tester", "tests passed"),
    MissionEventType.FIXER_REPAIRED_ISSUE: ("Fixer", "repaired issue"),
    MissionEventType.REVIEWER_REVIEWED: ("Reviewer", "reviewed output"),
    MissionEventType.VERIFIER_APPROVED_BUILD: ("Verifier", "approved build"),
    MissionEventType.LEARNING_RECORDED_PATTERN: ("Learning Engine", "recorded new pattern"),
    MissionEventType.EXPERIENCE_UPDATED_SKILL: ("Experience", "updated skill"),
    MissionEventType.PLUGIN_LOADED: ("Plugin OS", "loaded plugin"),
    MissionEventType.MISSION_COMPLETED: ("Mission", "completed"),
    MissionEventType.MISSION_FAILED: ("Mission", "failed"),
}

def source_for_event(event_type: str) -> str:
    return EVENT_LABELS.get(event_type, ("System", event_type))[0]

def default_message_for_event(event_type: str) -> str:
    return EVENT_LABELS.get(event_type, ("System", event_type))[1]
