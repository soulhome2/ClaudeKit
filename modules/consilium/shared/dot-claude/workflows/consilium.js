// ClaudeKit {{kit_version}}, модуль consilium. Общий файл: правится в ClaudeKit.
// Образец — IM, .claude/workflows/verification-audit.js.
export const meta = {
  name: 'consilium',
  description: 'Консилиум {{name}}: независимые аналитики, аудиторы проверяют их утверждения, председатель сводит итог',
  whenToUse: 'Критичный вопрос, где одно мнение ненадёжно. Вопрос и промпты — prompts/consilium.md. args: {date: "ГГГГ-ММ-ДД", analysts?: 3}',
  phases: [
    { title: 'Аналитики', detail: 'независимо, не больше трёх сразу, каждый пишет a<N>.md' },
    { title: 'Аудит', detail: 'аудиторы проверяют утверждения аналитиков' },
    { title: 'Консилиум', detail: 'итог из подтверждённого и таблица решений' },
  ],
}

// Тексты — в prompts/consilium.md, здесь только порядок запуска: правка промпта не требует правки сценария.
const PROMPTS = 'prompts/consilium.md'

const date = args && args.date
if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '')) {
  throw new Error('Нужна дата запуска: args = {date: "ГГГГ-ММ-ДД"}')
}
const N = Math.max(2, Math.min(5, (args && args.analysts) || 3))
const dir = `reviews/${date}/consilium`
// Не больше трёх агентов сразу: в IM пятеро вместе переполнили память и уронили VS Code
const BATCH = 3

const WRITTEN = {
  type: 'object',
  properties: {
    path: { type: 'string', description: 'Файл, куда записан ответ' },
    items: { type: 'integer', description: 'Сколько утверждений (у аудитора — проверенных)' },
    summary: { type: 'string', description: 'Главное в 2–3 фразах' },
  },
  required: ['path', 'items', 'summary'],
}

const own = path => `Запиши ответ целиком в ${path} (каталог создай, если его нет). ` +
  'Больше ничего в репозитории не меняй и не коммить. Раздел «Как запускать» в файле промптов — для человека, пропусти его.'

phase('Аналитики')
const roles = Array.from({ length: N }, (_, i) => ({ role: `А${i + 1}`, file: `a${i + 1}.md` }))
const analysts = []
for (let i = 0; i < roles.length; i += BATCH) {
  analysts.push(...(await parallel(roles.slice(i, i + BATCH).map(a => () => agent(
    `Ты — аналитик ${a.role}. Открой ${PROMPTS}: твои инструкции — блоки «Общая часть — всем агентам» ` +
    `и «Аналитик», твоя роль — ${a.role} (если в таблице ролей её нет — отвечай на вопрос целиком). ` +
    `Работай независимо: файлы других аналитиков в ${dir} не читай. ` + own(`${dir}/${a.file}`),
    { label: a.role, phase: 'Аналитики', schema: WRITTEN },
  )))).filter(Boolean))
}
if (!analysts.length) throw new Error('Ни один аналитик не ответил')
if (analysts.length < N) log(`Ответили ${analysts.length} из ${N} аналитиков — аудит идёт по тем, что есть`)
const answers = analysts.map(a => a.path).join(', ')

phase('Аудит')
const audit = await agent(
  `Ты — аудитор. Открой ${PROMPTS}: твои инструкции — блоки «Общая часть — всем агентам» и «Аудитор». ` +
  `Ответы аналитиков: ${answers}. ` + own(`${dir}/audit.md`),
  { label: 'аудитор', phase: 'Аудит', schema: WRITTEN },
)

phase('Консилиум')
const consilium = await agent(
  `Ты — председатель консилиума. Открой ${PROMPTS}: твои инструкции — блоки «Общая часть — всем агентам» ` +
  `и «Консилиум». Ответы аналитиков: ${answers}. Отчёт аудитора: ${audit ? audit.path : 'нет — все утверждения «не проверить»'}. ` +
  own(`${dir}/consilium.md`),
  { label: 'консилиум', phase: 'Консилиум', schema: WRITTEN },
)

return { analysts, audit, consilium }
