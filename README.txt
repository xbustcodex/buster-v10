Buster Self Improvement compatibility layer
=============================================

Copy the contained `buster` folder into:

    C:\Users\xkali\new_ai\buster-v10

Allow Windows to merge the folders and replace the two compatibility modules
already installed.

This installs forwarding modules for:

Apply package:
- apply_changes_worker.py
- backup_manager.py
- rollback_manager.py
- change_manifest.py
- patch_applier.py

Session package:
- repair_session.py
- repair_session_store.py
- session_manager.py

The real implementations remain inside:
- self_improvement\apply\
- self_improvement\session\
