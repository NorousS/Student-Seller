# Telegram Integration Guide

## Два способа интеграции

### 1. Bot API (текущий, простой)

**Используется сейчас:**
- `scripts/tg_notify.py` - отправка уведомлений
- `scripts/tg_listener.py` - прослушивание команд
- `scripts/check_telegram.py` - проверка новых сообщений

**Настройка:**
```bash
export TELEGRAM_BOT_TOKEN="8687950525:AAEty7ITx2eOYhd3tPwNkTBcvX_CBWBH7ig"
export TELEGRAM_CHAT_ID="1029414609"
```

**Примеры использования:**

```bash
# Отправить уведомление
python scripts/tg_notify.py "Сообщение"

# Проверить новые сообщения
python scripts/check_telegram.py --last 5

# Вывести в JSON
python scripts/check_telegram.py --json

# Слушать непрерывно
python scripts/tg_listener.py --poll
```

**Ограничения:**
- Только публичные бот-команды
- Нельзя читать личные сообщения пользователя
- Работает только с ботом

---

### 2. MCP Telegram (полный доступ)

**Установлен:** ✅ `uv tool install mcp-telegram`

**Возможности:**
- 📨 Отправка/редактирование/удаление сообщений
- 🔍 Поиск по чатам и сообщениям
- 📝 Управление черновиками
- 📂 Скачивание медиа из чатов
- 🔗 Доступ к личным сообщениям

**Настройка (требуется API ID/Hash):**

1. Получить API credentials:
   - Перейти на https://my.telegram.org/apps
   - Войти с номером телефона
   - Создать приложение
   - Скопировать `api_id` и `api_hash`

2. Выполнить логин:
   ```bash
   mcp-telegram login
   # Ввести api_id, api_hash, номер телефона
   ```

3. Настроить MCP сервер в `.mcp/settings.json`:
   ```json
   {
     "mcpServers": {
       "telegram": {
         "command": "mcp-telegram",
         "args": ["start"],
         "env": {
           "API_ID": "your_api_id",
           "API_HASH": "your_api_hash"
         }
       }
     }
   }
   ```

4. Перезапустить Copilot CLI

**Использование:**

После настройки MCP, агенты смогут:
- Читать личные сообщения пользователя
- Отправлять сообщения от имени пользователя
- Искать в истории чатов
- Скачивать файлы из сообщений

---

## Workflow с проверкой Telegram

### При отправке уведомлений

```python
# В конце работы агента
await send_notification("✅ Задача завершена")

# Сразу проверить, не ответил ли пользователь
messages = check_new_messages()
if messages:
    process_user_feedback(messages)
```

### Периодическая проверка

Добавлено в глобальные инструкции:
- Каждые 30 минут проверять Telegram
- При отправке уведомления — тоже проверить входящие
- Тайм-аут проверки: 30 секунд

```bash
# Проверка с таймаутом
python scripts/tg_listener.py --timeout 30
```

---

## Текущий статус

✅ Bot API настроен и работает
✅ Скрипты для отправки/проверки созданы
✅ MCP Telegram установлен
⏳ Ждём API ID/Hash для полной настройки MCP

---

## Безопасность

**Bot API:**
- Токен бота хранится в переменных окружения
- Фильтрация по chat_id (только от владельца)

**MCP Telegram:**
- API credentials НЕ коммитить в Git
- Хранить в `.env` или environment variables
- Session файл содержит авторизацию — не делиться

---

## Troubleshooting

**"Database is locked":**
- Запущено несколько экземпляров `mcp-telegram`
- Решение: `pkill -f "mcp-telegram"` (Linux/Mac) или Task Manager (Windows)

**"TELEGRAM_BOT_TOKEN not set":**
```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

**Bot не отвечает:**
- Проверить токен: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Проверить chat_id: отправить `/start` боту

---

## Ссылки

- [Bot API Documentation](https://core.telegram.org/bots/api)
- [MCP Telegram GitHub](https://github.com/dryeab/mcp-telegram)
- [Telegram Apps Portal](https://my.telegram.org/apps)
