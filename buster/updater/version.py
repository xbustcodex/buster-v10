from packaging import version

def clean_version(value):
    return str(value).strip().lower().lstrip("v")

def is_newer(latest, current):
    try:
        return version.parse(clean_version(latest)) > version.parse(clean_version(current))
    except Exception:
        return False
