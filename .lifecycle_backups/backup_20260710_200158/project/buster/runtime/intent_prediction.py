from __future__ import annotations
from typing import Any, Dict, List
from .storage import append_json, now
from pathlib import Path
PREDICTIONS_PATH = Path('data/intent_predictions.json')
class IntentPredictionEngine:
    def predict(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        text=' '.join(str(o.get('summary','')) + ' ' + str(o.get('type','')) for o in observations).lower()
        intent='general_work'; confidence=0.55; actions=[]
        if 'android studio' in text or 'pixel' in text or 'logcat' in text:
            intent='android_development'; confidence=0.88; actions=['prepare_android_plugin','monitor_logcat','index_current_project']
        elif 'esp32' in text or 'arduino' in text or 'serial' in text:
            intent='embedded_development'; confidence=0.86; actions=['prepare_arduino_plugin','monitor_serial','load_hardware_context']
        elif 'python' in text or 'tkinter' in text:
            intent='python_development'; confidence=0.82; actions=['prepare_python_tools','run_tests_when_safe']
        prediction={'intent':intent,'confidence':confidence,'suggested_actions':actions,'created_at':now(),'observations':observations[-5:]}
        append_json(PREDICTIONS_PATH, prediction, limit=300)
        return prediction
