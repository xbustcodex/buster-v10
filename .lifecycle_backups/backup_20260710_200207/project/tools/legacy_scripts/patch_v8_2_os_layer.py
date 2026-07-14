from pathlib import Path

path = Path("buster/brain/engine.py")
text = path.read_text(encoding="utf-8")

if "from buster.os_layer.os_layer import OSLayer" not in text:
    text = text.replace(
        "from buster.version import VERSION\n",
        "from buster.version import VERSION\nfrom buster.os_layer.os_layer import OSLayer\n",
        1
    )

needle = "        cmd = text.strip().lower()\n"

insert = '''        os_reply = OSLayer().handle(text)
        if os_reply is not None:
            return os_reply

'''

if "os_reply = OSLayer().handle(text)" not in text:
    text = text.replace(needle, needle + insert, 1)

path.write_text(text, encoding="utf-8")
print("Buster OS Layer wired into BrainEngine.")
