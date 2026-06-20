# TheMatch

**Чисто статическая PWA** для расчёта эзотерической совместимости двух людей по
датам рождения: зодиак, биоритмы и нумерология. Весь расчёт идёт **в браузере** —
ни бэкенда, ни базы данных, ни сети. Деплоится как статика (Vercel preset «Other»),
работает оффлайн.

> История: раньше был Telegram-бот, затем Flask-бэкенд на Vercel. Всё удалено.
> Фронтенд использовал только расчёт совместимости (чистая математика), поэтому
> логика перенесена в JS и бэкенд больше не нужен. Старый код — в истории git.

> **Важно для Claude:** обновляй этот файл при каждой значимой правке (новые
> файлы/структура, изменения в логике расчёта, деплой). См. «Поддержка файла» внизу.

---

## Стек

- **Только статика:** HTML + CSS + vanilla JS, без сборки и зависимостей.
- **PWA:** Service Worker (`sw.js`, cache-first, оффлайн) + `manifest.json`.
- **Деплой:** Vercel как статический сайт. Framework Preset = **Other**, без build
  command. Раздаётся содержимое `public/`. Никаких env-переменных. Root Directory
  можно оставить `.` (тогда `public/` — output) — см. «Деплой» ниже.

## Структура

```
public/             ← всё приложение (статика, раздаётся как сайт)
  index.html        ← разметка: форма ввода двух дат + контейнер результата
  logic.js          ← ВСЯ логика расчёта (зодиак/биоритмы/нумерология + тексты).
                      Глобальный объект `TheMatch.compute(date1, date2)`
  app.js            ← UI: обработка формы, вызов TheMatch.compute, рендер карточек
  style.css         ← стили, mobile-first (max-width контейнера, тёмная тема)
  sw.js             ← Service Worker (прекэш ассетов, cache-first)
  manifest.json     ← PWA-манифест (standalone, portrait)
  icons/icon.svg    ← иконка приложения
CLAUDE.md
.gitignore
```

## Как это работает

1. Пользователь выбирает две даты рождения (`<input type="date">`) и жмёт кнопку.
2. `app.js` (`handleCalculate`) берёт значения, конвертит ISO → `Date`
   (`isoToDate`) и зовёт **`TheMatch.compute(d1, d2)`** из `logic.js`.
3. `logic.js` считает три блока и собирает итог:
   **`total = zodiac*0.35 + biorhythm*0.35 + numerology*0.30`**.
   Все под-оценки **симметричны** — результат не зависит от порядка дат
   (`compute(A,B) == compute(B,A)`): матрицы зодиака/нумерологии содержат
   несимметричные пары, поэтому берётся среднее двух направлений.
4. `app.js` (`renderResults`) рисует hero-кольцо и карточки (зодиак/биоритмы/
   нумерология) из возвращённого объекта.

### Контракт объекта результата (`TheMatch.compute` → `renderResults`)

```
{ total, total_emoji, total_phrase,
  zodiac:     { score, sign1, sign2, sign1_name, sign2_name,
                sign1_description, sign2_description,
                element1, element2, element1_emoji, element2_emoji,
                signs_score, elements_score, signs_emoji, elements_emoji,
                signs_phrase, elements_phrase },
  biorhythm:  { score, score_emoji, total_description,
                rhythms: { heart|intuitive|higher: { score, emoji,
                                                      person1, person2, description } } },
  numerology: { score, score_emoji, number1, number2,
                number1_description, number2_description,
                partnership_number, partnership_description, phrase } }
```

Меняешь форму этого объекта в `logic.js` — синхронно правь рендер в `app.js`.

### Соглашения

- Вся «бизнес-логика» и тексты — в `logic.js`; `app.js` только UI и рендер.
- Значения совместимости — числа 0..100; эмодзи/фразы выбираются по диапазонам.
- Тексты на русском, настоящее время, позитивная градация от слабой к сильной связи.

## Деплой (Vercel)

- Подключить репозиторий, **Framework Preset = Other**, Build Command — пусто,
  Output/раздаётся `public/`. Если Vercel не подхватывает `public/` как корень
  сайта — задать **Output Directory = `public`** (или Root Directory = `public`).
- Переменные окружения не нужны. БД/бэкенда нет.

## Локальный запуск

Любой статический сервер из `public/` (Service Worker требует http, не `file://`):

```bash
cd public
python -m http.server 8000   # или: npx serve .
# открыть http://localhost:8000
```

---

## Git-воркфлоу

Правки **пушатся сразу в `master`** (по договорённости с владельцем):

```
git add .
git commit -m "описание"
git push origin master
```

Remote: `https://github.com/stasHrytsko/thematch.git`. Папка `.claude/` исключена
локально через `.git/info/exclude` и в репозиторий не попадает.

## Поддержка этого файла

Обновляй `CLAUDE.md` в том же коммите, что и правки, когда меняется:
- структура каталогов / расположение файлов;
- логика расчёта (`logic.js`): формула, матрицы, тексты, форма результата;
- контракт между `logic.js` и `app.js`;
- настройки деплоя Vercel (preset, Output/Root Directory).
