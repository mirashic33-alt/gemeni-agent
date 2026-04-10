# Gemeni Agent — Журнал проделанной работы

> Что сделано, какие проблемы встречались и как их решали.

---

## Этап 1 — Структура проекта

**Сделано:**
- Создана структура папок: `core/`, `llm/`, `tools/`, `channels/telegram/`, `ui/`, `workspace/`, `data/`
- `ui_export.pyw` → `ui/main_window.py`, класс переименован `ExportedUI` → `MainWindow`
- `theme_config.py` → `ui/theme_config.py`
- Во всех пакетах созданы `__init__.py`
- `main.py` — единая точка входа

---

## Этап 2 — Тема и диалог настроек

**Сделано:**
- `ui/settings_dialog.py` — три поля: Gemini API Key, Telegram Bot Token, Telegram Chat ID
- Поля API Key и Token скрыты (`EchoMode.Password`)
- Тема применяется глобально через `app.setStyleSheet(build_qss(STATE))`

**Проблема:** диалог настроек открывался белым.  
**Причина:** стиль был привязан к `QWidget#preview_panel`, а не ко всем виджетам.  
**Решение:** перенесли применение стиля на уровень `QApplication`, добавили правила `QWidget, QDialog {}` и `QLineEdit {}` в `build_qss()`.

---

## Этап 3 — Шифрование ключей (Windows DPAPI)

**Сделано:**
- `data/keystore.py` — шифрование через Windows DPAPI (`ctypes`, без сторонних зависимостей)
- Ключи хранятся в `data/keys.enc` — бинарный зашифрованный блоб
- Привязаны к Windows-аккаунту: на другой машине или под другим пользователем не расшифруются
- `settings_dialog.py` читает/пишет через `keystore.get()` / `keystore.save_all()`
- `main.py` вызывает `keystore.load_if_exists()` при старте — разблокировка прозрачная, без пароля
- `.env` полностью убран

---

## Этап 4 — Провайдер Gemini и фоновая инициализация

**Сделано:**
- `llm/provider.py` — клиент Gemini, модель `gemini-3-flash-preview`
- `data/logger.py` — кастомный `_TailFileHandler`: держит последние 300 строк, разделитель сессий
- Лог в корне проекта: `agent.log`
- `core/startup.py` — `StartupWorker(QThread)`: читает ключи → проверяет → создаёт клиент → пингует → эмитит `done`
- После загрузки: заголовок `Gemeni · <модель>`, статус `Готов. · <модель>`
- Вывод в консоль убран — только файл

**Проблемы:**

1. **SDK:** начали с `google-generativeai` (старый). Железное правило — только `from google import genai` (`pip install google-genai`).

2. **Модель 404:** пробовали `gemini-3.1-pro-preview`, `gemini-3.0-pro-preview` — оба не работали с ключом пользователя. Оставили одну константу `gemini-3-flash-preview`.

3. **`response.text` был `None` при пинге:** изменили запрос на `"Say: ok"` и проверяем `response.candidates`.

4. **`load_dotenv`:** самописный парсер `.env` заменён на `python-dotenv`, затем полностью убран в пользу keystore.

---

## Этап 5 — Чат и память сессии

**Сделано:**
- `core/message_worker.py` — `MessageWorker(QThread)`: вызывает `provider.send()` в фоне
- `Enter` = отправить, `Shift+Enter` = новая строка (через `eventFilter`)
- Кнопка Send блокируется на время запроса
- `client.chats.create(history=gemini_history)` — сессия с полной историей при старте
- Конвертация: наш `role: "agent"` → Gemini `role: "model"`
- `data/chat_history.py` — JSON в `workspace/chat_history.json`, лимит 100 сообщений
- При очистке чата — сессия пересоздаётся пустой

**Проблема:** каждое сообщение отправлялось как отдельный запрос, модель ничего не помнила.  
**Решение:** заменили `generate_content()` на `client.chats.create()` + `chat.send_message()`.

---

## Этап 6 — Статус-бар и мониторинг системы

**Сделано:**
- Статус-бар разделён: левая (события) и правая (система)
- **Левая:** `Думаю... 3.45 сек` — живой таймер (QTimer 50 мс), затем `Готов. · 3.21 сек`
- **Правая:** `CPU: 23% | RAM: 64% | C: 93.1GB` — `psutil`, обновление каждые 2 сек

**Проблема:** таймер показывал только финальное значение, не тикал в реальном времени.  
**Причина:** таймер и мониторинг системы оба писали в правую часть и перебивали друг друга.  
**Решение:** таймер → левая часть, мониторинг → правая. Строгое разделение.

---

## Этап 7 — Telegram бот

**Сделано:**
- `channels/telegram/bot.py` — `python-telegram-bot` v20+ в отдельном потоке
- Двустороннее дублирование UI ↔ Telegram
- `core/bridge.py` — `AgentBridge(QObject)` с Qt-сигналами для thread-safe обмена
- `asyncio.run_coroutine_threadsafe()` для вызова async-методов из Qt-потока
- Команды `/start` и `/clear`. Typing-индикатор пока модель думает.

**Проблема:** `RuntimeError: This event loop is already running`.  
**Причина:** `run_polling()` в PTB v20+ конфликтует с `asyncio.run()`.  
**Решение:** явный `asyncio.new_event_loop()` в потоке + `async with self._app:` + `updater.start_polling()`.

---

## Не сделано (следующие этапы)

- `workspace/agent.md` → системный промпт (файл создан, пуст)
- `tools/filesystem.py` — работа с файлами в `workspace/`
- `ui/tray.py` — иконка в трее Windows
