# ClaudeKit {{kit_version}}. Общий файл: правится в ClaudeKit, в проекте перезаписывается командой update.
"""Общее для проверок набора: корень репозитория и параметры из .claude/kit.json."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def config():
    path = os.path.join(ROOT, ".claude", "kit.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"Нет {path}: проект не подключён к ClaudeKit")


def checks():
    return config().get("checks", {})


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def walk(paths, exts):
    """Файлы с расширениями exts под путями paths (относительно корня), без служебных каталогов."""
    for p in paths:
        full = os.path.join(ROOT, p)
        if os.path.isfile(full):
            yield full
            continue
        for dirpath, dirs, names in os.walk(full):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for n in sorted(names):
                if os.path.splitext(n)[1].lower() in exts:
                    yield os.path.join(dirpath, n)


def utf8_stdout():
    # Консоль Windows по умолчанию не UTF-8: без этого русские сообщения падают с UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
