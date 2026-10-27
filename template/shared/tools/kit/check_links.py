#!/usr/bin/env python3
# ClaudeKit {{kit_version}}. Общий файл: правится в ClaudeKit, в проекте перезаписывается командой update.
"""Ссылки в Markdown: относительная ссылка ведёт на существующий файл, якорь — на существующий заголовок.

Запуск из любой папки: python tools/kit/check_links.py
Пропустить файлы или каталоги — checks.links_ignore в .claude/kit.json (пути от корня, префиксом).
Внешние ссылки (http, mailto) не проверяются. Код выхода 1, если есть нерабочие.
"""
import os
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, checks, rel, utf8_stdout, walk  # noqa: E402

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def strip_code(lines):
    fence = False
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            continue
        if not fence:
            yield n, re.sub(r"`[^`]*`", "", line)


def slugs(path, cache={}):
    """Якоря заголовков так, как их строит GitHub."""
    if path in cache:
        return cache[path]
    seen, out = {}, set()
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for _, line in strip_code(lines):
        m = HEADING.match(line)
        if not m:
            continue
        text = re.sub(r"<[^>]+>|\[([^\]]*)\]\([^)]*\)", r"\1", m.group(2))
        slug = re.sub(r"[^\w\- ]", "", text.lower(), flags=re.UNICODE).replace(" ", "-")
        k = seen.get(slug, 0)
        seen[slug] = k + 1
        out.add(slug if k == 0 else f"{slug}-{k}")
    cache[path] = out
    return out


def main():
    utf8_stdout()
    ignore = tuple(checks().get("links_ignore", []))
    bad = total = 0
    for path in walk(["."], {".md"}):
        if ignore and rel(path).startswith(ignore):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        for n, line in strip_code(lines):
            for target in LINK.findall(line) + IMAGE.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                    continue
                total += 1
                file_part, _, anchor = target.partition("#")
                dest = path if not file_part else os.path.normpath(os.path.join(os.path.dirname(path), unquote(file_part)))
                problem = None
                if not os.path.exists(dest):
                    problem = "нет файла"
                elif anchor and dest.lower().endswith(".md") and not re.fullmatch(r"L\d+(-L\d+)?", anchor):
                    if unquote(anchor).lower() not in slugs(dest):
                        problem = "нет заголовка"
                if problem:
                    bad += 1
                    print(f"FAIL {rel(path)}:{n}: {target} — {problem}")
    print(f"Ссылок проверено: {total}, нерабочих: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
