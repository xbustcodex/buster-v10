from pathlib import Path

path = Path("buster/ui/main_window.py")
text = path.read_text(encoding="utf-8")

if "from buster.core.settings_store import SettingsStore" not in text:
    text = text.replace(
        "from buster.ui.settings_dialog import SettingsDialog\n",
        "from buster.ui.settings_dialog import SettingsDialog\nfrom buster.core.settings_store import SettingsStore\n"
    )

old_buttons = '("Agents","agents"),("System","system status")'
new_buttons = '("Agents","agents"),("Settings","settings"),("System","system status")'

if old_buttons in text and new_buttons not in text:
    text = text.replace(old_buttons, new_buttons)

needle = 'self.chat.append(f"You: {text}"); self.set_mode("thinking")'
insert = '''self.chat.append(f"You: {text}"); self.set_mode("thinking")
        cmd = text.strip().lower()

        if cmd in ["settings", "open settings"]:
            dlg = SettingsDialog(self.settings, self)
            if dlg.exec():
                values = dlg.get_values()

                self.settings.always_on_top = values["always_on_top"]
                self.settings.wake_word = values["wake_word"]
                self.settings.data_dir = values["data_dir"]
                self.settings.logs_dir = values["logs_dir"]
                self.settings.screenshots_dir = values["screenshots_dir"]

                SettingsStore().save(self.settings)
                self.chat.append("Buster: Settings saved.")
            self.set_mode("standby")
            return'''

if 'cmd in ["settings", "open settings"]' not in text:
    text = text.replace(needle, insert)

path.write_text(text, encoding="utf-8")
print("Persistent settings wired into main_window.py")
