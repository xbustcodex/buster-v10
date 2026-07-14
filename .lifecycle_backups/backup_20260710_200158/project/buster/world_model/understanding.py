class UnderstandingEngine:
    def infer_context(self, observations):
        text = " ".join(o.get("summary", "") if isinstance(o, dict) else getattr(o, "summary", "") for o in observations).lower()
        context = {"mode": "idle", "signals": []}
        if "android studio" in text or "gradle" in text or "logcat" in text:
            context["mode"] = "android_development"
            context["signals"].append("android_workflow")
        if "esp32" in text or "arduino" in text:
            context["mode"] = "hardware_development"
            context["signals"].append("hardware_workflow")
        if "error" in text or "failed" in text or "crash" in text:
            context["signals"].append("needs_attention")
        return context

    def recommend(self, context):
        mode = context.get("mode")
        if mode == "android_development":
            return "Prepare Android tooling, monitor builds, and watch Logcat for errors."
        if mode == "hardware_development":
            return "Prepare hardware plugins and watch serial/device connection status."
        if "needs_attention" in context.get("signals", []):
            return "Create a mission for diagnosis and route it through Tester, Fixer, and Verifier."
        return "Stay present, observe quietly, and avoid interrupting unless something meaningful changes."
