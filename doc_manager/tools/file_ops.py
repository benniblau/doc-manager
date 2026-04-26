import os
import re
import shutil


_UMLAUT_MAP = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
    "ß": "ss",
})


def sanitize_filename(name: str) -> str:
    name = name.translate(_UMLAUT_MAP)
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = re.sub(r"[\s]+", "_", name)
    return name.strip("_")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def move_file(src: str, dst: str) -> None:
    ensure_dir(os.path.dirname(dst))
    shutil.move(src, dst)


def copy_file(src: str, dst: str) -> None:
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)


def write_text(path: str, content: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
