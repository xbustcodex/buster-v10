from __future__ import annotations
from buster.workspace.runtime_dashboard import RuntimeDashboard
class RuntimeWidgetModel:
    def build(self):
        snap=RuntimeDashboard().snapshot()
        return {'heading':'Buster Runtime','lines':['Status: %s' % snap.get('status'),'Ticks: %s' % snap.get('tick_count'),'Mode: %s' % snap.get('mode'),'Health: %s' % snap.get('health')], 'snapshot': snap}
