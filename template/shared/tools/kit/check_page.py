#!/usr/bin/env python3
# ClaudeKit {{kit_version}}. Общий файл: правится в ClaudeKit, в проекте перезаписывается командой update.
"""Прототип открывается: нет ошибок JS, не потеряны свои файлы, страница не шире экрана телефона.

Запуск: python tools/kit/check_page.py [--shots <папка>] [страница.html …]
Страницы по умолчанию — checks.pages в .claude/kit.json. Для каждой — обе темы (атрибут
data-theme на <html>, как в ONE PSIM) и ширины 1440 и 360 px. --shots — сохранить снимки
<папка>/<страница>-<тема>-<ширина>.png, чтобы посмотреть глазами.

FAIL — ошибка JS или не загрузился файл из репозитория (код выхода 1).
ЗАМЕЧАНИЕ — не загрузился внешний ресурс (шрифт, CDN) или горизонтальная прокрутка на 360 px.
Нужен playwright (pip install playwright && playwright install chromium). Нет его — «НЕ ПРОГНАНО», код 2.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, checks, utf8_stdout  # noqa: E402

WIDTHS = [(1440, 900), (360, 800)]
THEMES = ["light", "dark"]


def main():
    utf8_stdout()
    args = sys.argv[1:]
    shots = None
    if "--shots" in args:
        i = args.index("--shots")
        shots = os.path.abspath(args[i + 1])
        del args[i:i + 2]
        os.makedirs(shots, exist_ok=True)
    pages = args or checks().get("pages", [])
    if not pages:
        print("checks.pages в kit.json пуст — проверять нечего")
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("НЕ ПРОГНАНО: нет playwright (pip install playwright && playwright install chromium)")
        return 2

    root_url = "file://" + ("/" if not ROOT.startswith("/") else "") + ROOT.replace(os.sep, "/")
    bad = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for page_path in pages:
            full = os.path.join(ROOT, page_path)
            if not os.path.exists(full):
                print(f"FAIL {page_path}: нет файла")
                bad += 1
                continue
            url = root_url + "/" + page_path.replace(os.sep, "/")
            for w, h in WIDTHS:
                ctx = browser.new_context(viewport={"width": w, "height": h})
                page = ctx.new_page()
                errors, missing, external = [], set(), set()
                page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0]))
                page.on("console", lambda m: m.type == "error" and errors.append(m.text.splitlines()[0]))

                def failed(req):
                    (missing if req.url.startswith("file:") else external).add(req.url)

                page.on("requestfailed", failed)
                page.goto(url, wait_until="load")
                page.wait_for_timeout(800)
                for theme in THEMES:
                    page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                    page.wait_for_timeout(200)
                    if shots:
                        name = os.path.splitext(os.path.basename(page_path))[0]
                        page.screenshot(path=os.path.join(shots, f"{name}-{theme}-{w}.png"))
                    if w < 600:
                        over = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                        if over > 1:
                            print(f"ЗАМЕЧАНИЕ {page_path} [{theme}, {w}px]: шире экрана на {over} px")
                ctx.close()
                for e in dict.fromkeys(errors):
                    bad += 1
                    print(f"FAIL {page_path} [{w}px]: ошибка JS — {e}")
                for u in sorted(missing):
                    bad += 1
                    print(f"FAIL {page_path}: не загрузился {u.replace(root_url + '/', '')}")
                for u in sorted(external):
                    print(f"ЗАМЕЧАНИЕ {page_path}: не загрузился внешний {u}")
                if errors or missing:
                    break  # на второй ширине те же ошибки
        browser.close()
    print(f"Страниц: {len(pages)}, ошибок: {bad}" + (f", снимки — {shots}" if shots else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
