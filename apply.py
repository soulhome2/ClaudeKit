#!/usr/bin/env python3
"""ClaudeKit: перенести шаблон в проект и держать его в актуальном состоянии.

  python apply.py init   <проект> [--prefix lpr --name LPR --title "…" --repo URL] [--with consilium]
  python apply.py update <проект> [<проект> …]   — обновить общие файлы, добавить недостающие
  python apply.py check  <проект> [<проект> …]   — что разошлось с набором (код выхода 1)

Файлы шаблона двух видов:
  template/shared/ — общие: при update перезаписываются. Править их в ClaudeKit, не в проекте.
  template/seed/   — заготовки: создаются один раз, дальше принадлежат проекту, update их не трогает.
Модули (modules/<имя>/shared|seed) подключаются через --with или списком "modules" в kit.json.
Пресет проекта — projects/<имя папки проекта>/: kit.json и проектные заготовки (чек-лист, evals),
подготовленные заранее. init берёт их вместо общих заготовок; --prefix и --name тогда не нужны.

Папка dot-claude в наборе при переносе становится .claude: удалённые инструменты Claude не могут
писать в .claude, поэтому набор хранит её под другим именем.

Параметры проекта — в <проект>/.claude/kit.json. В путях __P__ заменяется на prefix,
в тексте {{ключ}} — на значение из kit.json (строки верхнего уровня) и {{kit_version}}.
Только стандартная библиотека Python 3.8+, работает на Windows и Linux.
"""
import argparse
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
KIT_JSON = os.path.join(".claude", "kit.json")
TEXT_EXT = {".md", ".py", ".js", ".mjs", ".json", ".yml", ".yaml", ".txt", ".css", ".html", ""}


def kit_version():
    with open(os.path.join(KIT, "VERSION"), encoding="utf-8") as f:
        return f.read().strip()


def load_cfg(project):
    path = os.path.join(project, KIT_JSON)
    if not os.path.exists(path):
        sys.exit(f"{project}: нет {KIT_JSON} — сначала init")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_cfg(project, cfg):
    path = os.path.join(project, KIT_JSON)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def roots(cfg):
    """(вид, каталог-источник) — сначала базовый шаблон, потом модули."""
    out = [("shared", os.path.join(KIT, "template", "shared")), ("seed", os.path.join(KIT, "template", "seed"))]
    for m in cfg.get("modules", []):
        base = os.path.join(KIT, "modules", m)
        if not os.path.isdir(base):
            sys.exit(f"Нет модуля {m} в {os.path.join(KIT, 'modules')}")
        out += [("shared", os.path.join(base, "shared")), ("seed", os.path.join(base, "seed"))]
    return out


def render(text, cfg):
    values = {k: v for k, v in cfg.items() if isinstance(v, str)}
    values["PREFIX"] = cfg["prefix"].upper()

    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"в kit.json нет ключа «{key}»")
        return values[key]

    return re.sub(r"\{\{(\w+)\}\}", sub, text)


def target(rel_path):
    """Путь в наборе → путь в проекте: dot-claude → .claude."""
    parts = rel_path.replace("\\", "/").split("/")
    return os.path.join(*[".claude" if x == "dot-claude" else x for x in parts])


def preset_dir(project):
    d = os.path.join(KIT, "projects", os.path.basename(os.path.normpath(project)))
    return d if os.path.isdir(d) else None


def apply_preset(project, cfg):
    """Проектные заготовки из пресета — только тех файлов, которых в проекте ещё нет."""
    d = preset_dir(project)
    out = []
    if not d:
        return out
    for dirpath, _, names in os.walk(d):
        for name in sorted(names):
            src = os.path.join(dirpath, name)
            rel = target(os.path.relpath(src, d))
            if rel == KIT_JSON:
                continue
            dst = os.path.join(project, rel)
            if os.path.exists(dst):
                continue
            with open(src, "rb") as f:
                data = f.read()
            if os.path.splitext(name)[1].lower() in TEXT_EXT:
                data = render(data.decode("utf-8"), cfg).encode("utf-8")
            write(dst, data)
            out.append(("seed", rel, "из пресета"))
    return out


def planned(cfg):
    """[(вид, путь в проекте, содержимое)]"""
    files = []
    for kind, root in roots(cfg):
        if not os.path.isdir(root):
            continue
        for dirpath, _, names in os.walk(root):
            for name in sorted(names):
                src = os.path.join(dirpath, name)
                rel = target(os.path.relpath(src, root)).replace("__P__", cfg["prefix"])
                with open(src, "rb") as f:
                    data = f.read()
                if os.path.splitext(name)[1].lower() in TEXT_EXT:
                    try:
                        data = render(data.decode("utf-8"), cfg).encode("utf-8")
                    except KeyError as e:
                        sys.exit(f"{src}: {e.args[0]}")
                files.append((kind, rel, data))
    return files


def same(path, data):
    if not os.path.exists(path):
        return False
    with open(path, "rb") as f:
        return f.read().replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n")


def write(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def sync(project, cfg, dry):
    changed = []
    for kind, rel, data in planned(cfg):
        dst = os.path.join(project, rel)
        if kind == "seed" and os.path.exists(dst):
            continue
        if same(dst, data):
            continue
        status = "нет файла" if not os.path.exists(dst) else (
            "отличается: новая версия набора, другие параметры kit.json или правка на месте" if kind == "shared" else "")
        changed.append((kind, rel, status))
        if not dry:
            write(dst, data)
    return changed


def report(project, changed, dry):
    verb = "разошлось" if dry else "записано"
    print(f"{project}: {verb} {len(changed)}")
    for kind, rel, status in changed:
        print(f"  [{'общий' if kind == 'shared' else 'заготовка'}] {rel}" + (f" — {status}" if status else ""))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["init", "update", "check"])
    p.add_argument("projects", nargs="+")
    p.add_argument("--prefix")
    p.add_argument("--name")
    p.add_argument("--title")
    p.add_argument("--repo", default="")
    p.add_argument("--with", dest="modules", action="append", default=[])
    p.add_argument("--force", action="store_true", help="init в проект, где уже есть свои скиллы")
    a = p.parse_args()
    version = kit_version()
    bad = 0

    for project in a.projects:
        project = os.path.abspath(project)
        if not os.path.isdir(project):
            sys.exit(f"Нет папки {project}")
        if os.path.abspath(project) == KIT:
            sys.exit("Набор нельзя применять к самому себе")

        if a.command == "init":
            path = os.path.join(project, KIT_JSON)
            preset = preset_dir(project)
            if os.path.exists(path):
                cfg = load_cfg(project)
                print(f"{project}: kit.json уже есть — беру параметры из него")
            elif preset and os.path.exists(os.path.join(preset, "dot-claude", "kit.json")):
                with open(os.path.join(preset, "dot-claude", "kit.json"), encoding="utf-8") as f:
                    cfg = json.load(f)
                print(f"{project}: параметры — из пресета {os.path.relpath(preset, KIT)}")
            else:
                # Проект со своими скиллами без kit.json (например, IM — оригинал набора) не трогать
                if os.path.isdir(os.path.join(project, ".claude", "skills")) and not a.force:
                    sys.exit(f"{project}: уже есть свои скиллы и нет kit.json — набор не применяю. "
                             "Если это осознанно — --force")
                if not a.prefix or not a.name:
                    sys.exit("init: нужны --prefix и --name")
                if not re.fullmatch(r"[a-z][a-z0-9]*", a.prefix):
                    sys.exit("--prefix — латиница в нижнем регистре и цифры, например lpr")
                cfg = {
                    "prefix": a.prefix,
                    "name": a.name,
                    "title": a.title or a.name,
                    "repo": a.repo,
                    "review_scope": f"требований и прототипа {a.name}",
                    "modules": [],
                    "checks": {"ids": [], "pages": [], "links_ignore": []},
                }
            cfg["modules"] = sorted(set(cfg.get("modules", [])) | set(a.modules))
            cfg["kit_version"] = version
            save_cfg(project, cfg)
            from_preset = apply_preset(project, cfg)
            report(project, from_preset + sync(project, cfg, dry=False), dry=False)

        elif a.command == "update":
            cfg = load_cfg(project)
            cfg["kit_version"] = version
            save_cfg(project, cfg)
            report(project, sync(project, cfg, dry=False), dry=False)

        else:
            cfg = load_cfg(project)
            changed = sync(project, dict(cfg, kit_version=cfg.get("kit_version", version)), dry=True)
            if cfg.get("kit_version") != version:
                print(f"{project}: набор {cfg.get('kit_version')} → есть {version}, нужен update")
                bad += 1
            report(project, changed, dry=True)
            bad += bool(changed)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
