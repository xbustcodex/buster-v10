# Buster workspace package

try:
    from .mission_control_dashboard import MissionControlDashboard
except Exception:  # keep imports safe during partial installs
    MissionControlDashboard = None
