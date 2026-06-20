# TheMatch PWA

Веб-приложение (PWA) для расчёта эзотерической совместимости двух людей по датам
рождения: зодиак, биоритмы и нумерология. Раньше в репозитории был и Telegram-бот —
он полностью удалён, остался **только PWA**.

> **Важно для Claude:** этот файл нужно обновлять при каждой значимой правке проекта
> (новый/удалённый эндпоинт, изменение схемы БД, смена структуры, новые переменные
> окружения, изменения деплоя). См. раздел «Поддержка этого файла» внизу.

---

## Стек и деплой

- **Backend:** Python + Flask как serverless-функции на **Vercel** (`api/*.py`).
- **БД:** **Postgres** (Vercel Postgres / Supabase) через `psycopg2`, строка
  подключения в `DATABASE_URL`.
- **Frontend:** vanilla JS PWA (статика в корне) — без фреймворков и сборки, с
  Service Worker (оффлайн) и manifest (устанавливаемое приложение).
- **Деплой:** Vercel, **zero-config** (без `vercel.json`). Vercel сам раздаёт
  статику из корня и поднимает `api/*.py` как Python-функции (определяется по
  `requirements.txt`). В настройках проекта **Root Directory = `.`** (корень репо).

## Структура

Раскладка под Vercel: статика и `api/` в корне репозитория.

```
api/                ← serverless-эндпоинты Flask (по файлу на маршрут)
  compatibility.py  ← POST /api/compatibility — основной расчёт
  user.py           ← POST /api/user — создать/получить пользователя
  feedback.py       ← POST /api/feedback — сохранить отзыв
  history.py        ← GET  /api/history?user_id=&limit= — история проверок
services/           ← ядро расчётов (чистая логика, без Flask/БД)
  zodiac.py         ← знаки, стихии, их совместимость
  biorhythm.py      ← биоритмы (heart / intuitive / higher)
  numerology.py     ← числа судьбы и партнёрства
  descriptions.py   ← тексты, фразы, эмодзи под диапазоны (самый большой файл)
database/db.py      ← Postgres-слой: класс Database + get_connection/init_db
index.html          ← фронтенд PWA (раздаётся как `/`)
app.js              ← вся UI-логика: форма, запрос к API, рендер результата
style.css           ← стили (mobile-first, max-width контейнера)
sw.js               ← Service Worker (кэш статики, оффлайн-ответ для /api)
manifest.json       ← PWA-манифест
icons/icon.svg      ← иконка приложения
utils.py            ← get_logger, add_cors, cors_preflight
requirements.txt    ← flask, psycopg2-binary, python-dotenv
.env.example        ← шаблон переменных окружения (DATABASE_URL)
```

> Общие модули (`services/`, `database/`, `utils.py`) попадают в бандл функции
> через трассировку импортов Vercel — отдельный `includeFiles` не нужен.

## Как это работает

1. Пользователь вводит две даты рождения в `index.html` → `app.js` шлёт `POST
   /api/compatibility` с `{date1, date2, user_id?}` в формате `ДД.ММ.ГГГГ`.
2. `api/compatibility.py` валидирует даты, вызывает три сервиса и считает итог:
   **`total = zodiac*0.35 + biorhythm*0.35 + numerology*0.30`**.
   Все под-оценки **симметричны** — результат не зависит от порядка дат
   (`compat(A,B) == compat(B,A)`). Матрицы зодиака/нумерологии содержат
   несимметричные пары, поэтому в `get_signs_compatibility` и
   `NumerologyService.calculate_compatibility` берётся среднее двух направлений.
3. Возвращает JSON со счётом, эмодзи, описаниями и фразами; `app.js` рендерит
   результат (кольца, секции). Если передан `user_id` — результат пишется в
   `checks_history`.

### Соглашения по коду API

- Каждый `api/*.py` — самостоятельное Flask-приложение, экспортирующее `app`
  (модель Vercel «один файл = одна функция»).
- В начале файла: `sys.path.insert(0, .. )`, чтобы импортировать `utils`,
  `services`, `database` из корня. **Не ломать этот путь при перемещении файлов.**
- Все ответы оборачиваются в `add_cors(...)`; на `OPTIONS` — `cors_preflight(...)`.
- БД используется как контекст-менеджер: `with Database() as db: ...`
  (соединение на один запрос, Vercel-функции stateless).
- Даты от клиента — строки `ДД.ММ.ГГГГ`; в БД `birth_date` хранится как `YYYY-MM-DD`.

### Схема БД (`database/db.py`)

- `users(user_id PK, username, free_checks=10, paid_checks=0, birth_date)`
- `checks_history(id, user_id, date1, date2, compatibility_score, check_date)`
- `feedback(id, user_id, text, created_at)`
- `init_db()` создаёт таблицы (idempotent), запускать один раз при деплое.

> Поля `free_checks` / `paid_checks` есть в схеме, но монетизация **не реализована**.

## Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env          # вписать DATABASE_URL
# фронтенд: открыть index.html (или раздать статикой из корня)
# api: через `vercel dev` либо запустить нужный api/*.py как Flask-приложение
```

## Переменные окружения

- `DATABASE_URL` — строка подключения Postgres (обязательно для эндпоинтов с БД).

## Заметки

- **Иконки PWA** — пока используется только `icons/icon.svg` (manifest и
  `apple-touch-icon` ссылаются на него). Для лучшей поддержки iOS стоит добавить
  растровые `icon-192.png` / `icon-512.png` и вернуть их в `manifest.json`.

---

## Git-воркфлоу

Правки в этой папке **пушатся сразу в `master`** (по договорённости с владельцем):

```
git add .
git commit -m "описание"
git push origin master
```

Remote: `https://github.com/stasHrytsko/thematch.git`. Папка `.claude/` исключена
локально через `.git/info/exclude` и в репозиторий не попадает.

## Поддержка этого файла

Обновляй `CLAUDE.md` в том же коммите, что и сами правки, когда меняется:
- набор эндпоинтов `api/*` или их контракты (тело запроса/ответа);
- схема БД или интерфейс `database/db.py`;
- структура каталогов / расположение файлов;
- переменные окружения, зависимости (`requirements.txt`), настройки деплоя
  Vercel (Root Directory, наличие/отсутствие `vercel.json`);
- формула расчёта совместимости или состав сервисов.
