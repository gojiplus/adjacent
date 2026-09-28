import os
import re
import tempfile
from pathlib import Path

START = b"<!-- adjacent:start -->"
END = b"<!-- adjacent:end -->"


def bounds(data):
    if data.count(START) != 1 or data.count(END) != 1:
        raise ValueError(
            "README must contain exactly one adjacent:start/end marker pair"
        )
    start, end = data.index(START) + len(START), data.index(END)
    if start > end:
        raise ValueError("README markers must be in start/end order")
    return start, end


def escape(text):
    text = " ".join((text or "").split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{}\[\]()!|#])", r"\\\1", text)


def render(original, recommendations):
    start, end = bounds(original)
    newline = "\r\n" if b"\r\n" in original else "\n"
    lines = ["", "", "## 🔗 Adjacent Repositories", ""]
    for item in recommendations:
        name = item.full_name
        desc = escape(item.description)
        lines.append(
            f"- [{name}](https://github.com/{name})" + (f" — {desc}" if desc else "")
        )
    if not recommendations:
        lines.append("No related repositories found.")
    lines.extend(
        ["", "_Powered by [Adjacent](https://github.com/gojiplus/adjacent)_", "", ""]
    )
    return original[:start] + newline.join(lines).encode() + original[end:]


def write_atomic(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.chmod(path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
