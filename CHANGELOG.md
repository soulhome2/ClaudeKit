# Журнал изменений ClaudeKit

Версия — `VERSION`. Меняется при любой правке `template/shared/` или модулей: проекты видят её в `.claude/kit.json`, `apply.py check` показывает, кому нужен update.

## 1.0.0 — 2026-10-27

Первая версия, обобщена из IM (коммит `main` на 2026-10-27; IM не менялся).

- Скиллы `<p>-review` и `<p>-fix`: порядок работы и формат ревью из `im-review` / `im-fix`, проектное — в CLAUDE.md и `checklist.md`.
- Evals срабатывания скиллов: `run_triggers.py` из IM, имена скиллов из `kit.json`.
- Проверки `tools/kit/`: ссылки в Markdown, идентификаторы требований, запуск прототипа.
- Заготовки: CLAUDE.md, settings.json, checklist.md, triggers.md, reviews/README.md, .gitignore.
- Модуль `consilium` — из `verification-audit` IM.
- Папка `.claude` хранится в наборе как `dot-claude`, `apply.py` переименовывает при переносе.
- Пресеты `projects/LPR`, `projects/Retail`; `init` без параметров берёт настройки из пресета.
- `init` не применяет набор к проекту, где уже есть свои скиллы без `kit.json` (IM), — только с `--force`.
- Подключены LPR и Retail.
