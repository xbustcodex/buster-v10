from buster.os_layer.filesystem import FileSystemAccess
from buster.os_layer.windows_system import WindowsSystemAccess

class OSLayer:
    def __init__(self):
        self.fs = FileSystemAccess()
        self.windows = WindowsSystemAccess()

    def handle(self, text):
        cmd = text.strip()
        low = cmd.lower()

        if low in ["os roots", "approved folders"]:
            return self.fs.approved_folders()

        if low.startswith("approve folder "):
            return self.fs.approve_folder(cmd[len("approve folder "):].strip())

        if low.startswith("remove approved folder "):
            return self.fs.remove_folder(cmd[len("remove approved folder "):].strip())

        if low in ["list downloads", "show downloads"]:
            return self.fs.list_folder("~/Downloads")

        if low in ["list desktop", "show desktop"]:
            return self.fs.list_folder("~/Desktop")

        if low in ["list documents", "show documents"]:
            return self.fs.list_folder("~/Documents")

        if low.startswith("list folder "):
            return self.fs.list_folder(cmd[len("list folder "):].strip())

        if low.startswith("open file "):
            return self.fs.open_path(cmd[len("open file "):].strip())

        if low.startswith("open folder "):
            return self.fs.open_path(cmd[len("open folder "):].strip())

        if low.startswith("read file "):
            return self.fs.read_file(cmd[len("read file "):].strip())

        if low.startswith("find file "):
            return self.fs.find_files(cmd[len("find file "):].strip())

        if low.startswith("search files "):
            return self.fs.find_files(cmd[len("search files "):].strip())

        if low in ["disk usage", "disk space"]:
            return self.fs.disk_usage()

        if low in ["env", "environment"]:
            return self.windows.env_summary()

        if low in ["where python", "python path"]:
            return self.windows.where_python()

        if low in ["processes", "running processes"]:
            return self.windows.running_processes()

        return None
