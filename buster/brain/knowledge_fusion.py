def fuse_local_and_web(local_context: str, web_context: str) -> str:
    parts = []
    if local_context:
        parts.append("[LOCAL CONTEXT]\n" + local_context)
    if web_context:
        parts.append("[WEB CONTEXT]\n" + web_context)
    return "\n\n".join(parts)
