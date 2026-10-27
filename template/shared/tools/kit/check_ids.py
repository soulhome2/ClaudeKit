#!/usr/bin/env python3
# ClaudeKit {{kit_version}}. Общий файл: правится в ClaudeKit, в проекте перезаписывается командой update.
"""Идентификаторы требований: каждый определён ровно один раз, ссылки ведут на определённые.

Запуск: python tools/kit/check_ids.py [--unused]
Параметры — checks.ids в .claude/kit.json, список групп:
  {"pattern": "LPR-[A-Z]+-\\d+",        регулярное выражение идентификатора
   "files": ["Specification/ТЗ.md"],     где идентификаторы определяются
   "define": "table" | "heading" | "bullet",  определение — первая ячейка строки таблицы, заголовок
                                         или начало пункта списка («- **UI-01.** …»)
   "refs": ["Specification", "prototypes"]}  где искать ссылки (.md .html .js .json)
Диапазон «LPR-ACC-01…10» (или ...) считается ссылкой на каждый номер.

FAIL — повтор определения или ссылка на несуществующий идентификатор (код выхода 1).
ЗАМЕЧАНИЕ — определён, но нигде больше не упомянут (--unused — показать список).
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, checks, rel, utf8_stdout, walk  # noqa: E402

REF_EXT = {".md", ".html", ".htm", ".js", ".json", ".txt"}


def definitions(group):
    pat = group["pattern"]
    define = group.get("define", "table")
    if define == "heading":
        rx = re.compile(rf"^#{{1,6}}\s+\**({pat})\b")
    elif define == "bullet":
        rx = re.compile(rf"^\s*[-*]\s+\**({pat})\b")
    else:
        rx = re.compile(rf"^\|\s*\**({pat})\**\s*\|")
    found = defaultdict(list)
    for f in group["files"]:
        path = os.path.join(ROOT, f)
        with open(path, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                m = rx.match(line)
                if m:
                    found[m.group(1)].append((rel(path), n))
    return found


def references(group):
    pat = group["pattern"]
    rx = re.compile(rf"(?<![\w-])({pat})(?:\s*(?:…|\.\.\.)\s*(\d+))?(?![\w-])")
    refs = defaultdict(list)
    for path in walk(group.get("refs", group["files"]), REF_EXT):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                for m in rx.finditer(line):
                    ident, upto = m.group(1), m.group(2)
                    ids = [ident]
                    num = re.search(r"(\d+)$", ident)
                    if upto and num and int(upto) > int(num.group(1)):
                        width = len(num.group(1))
                        base = ident[: num.start()]
                        ids = [f"{base}{i:0{width}d}" for i in range(int(num.group(1)), int(upto) + 1)]
                    for i in ids:
                        refs[i].append((rel(path), n))
    return refs


def main():
    utf8_stdout()
    groups = checks().get("ids", [])
    if not groups:
        print("checks.ids в kit.json пуст — проверять нечего")
        return 0
    show_unused = "--unused" in sys.argv
    bad = 0
    for g in groups:
        defs, refs = definitions(g), references(g)
        print(f"{g['pattern']}: определено {len(defs)}")
        for ident, places in sorted(defs.items()):
            if len(places) > 1:
                bad += 1
                print(f"FAIL {ident} определён {len(places)} раза: " + ", ".join(f"{p}:{n}" for p, n in places))
        for ident, places in sorted(refs.items()):
            if ident not in defs:
                bad += 1
                p, n = places[0]
                more = f" (и ещё {len(places) - 1})" if len(places) > 1 else ""
                print(f"FAIL {p}:{n}: ссылка на {ident} — такого нет{more}")
        unused = [i for i, places in defs.items() if not (set(refs.get(i, [])) - set(places))]
        if unused:
            print(f"ЗАМЕЧАНИЕ без ссылок: {len(unused)} из {len(defs)}" + ("" if show_unused else " (список — --unused)"))
            if show_unused:
                for i in sorted(unused):
                    p, n = defs[i][0]
                    print(f"  {i} — {p}:{n}")
    print(f"Ошибок: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
