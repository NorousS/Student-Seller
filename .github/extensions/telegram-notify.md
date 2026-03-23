# Telegram Notifications Extension

Send notifications to Telegram about agent work progress.

## Tools

### notify_telegram

Send a message to Telegram.

**Parameters:**
- `message` (string, required): The message to send
- `type` (string, optional): Message type - "info", "question", "success", "error". Default: "info"

**Implementation:**

```python
import urllib.request
import urllib.parse
import json
import os

def notify_telegram(message: str, type: str = "info") -> str:
    """Send notification to Telegram."""
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables must be set"
    
    # Add emoji based on type
    emoji_map = {
        "info": "ℹ️",
        "question": "❓",
        "success": "✅", 
        "error": "❌",
        "warning": "⚠️"
    }
    emoji = emoji_map.get(type, "📢")
    
    full_message = f"{emoji} {message}"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": full_message,
        "parse_mode": "HTML"
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("ok"):
                return f"Message sent successfully"
            else:
                return f"Error: {result.get('description', 'Unknown error')}"
    except Exception as e:
        return f"Error sending message: {str(e)}"

# Execute
result = notify_telegram(message, type)
print(result)
```

## Setup Instructions

### 1. Create Telegram Bot

1. Open Telegram and find **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "My Agent Notifier")
4. Choose a username (e.g., "my_agent_notify_bot")
5. Copy the **token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

1. Start a chat with your new bot (click Start)
2. Find **@userinfobot** in Telegram
3. Send `/start` to it
4. Copy your **Id** number

### 3. Configure Environment

Add to your Copilot MCP config or shell environment:

```powershell
# PowerShell profile or session
$env:TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
$env:TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
```

Or add to `.github/copilot/mcp.json`:

```json
{
  "mcpServers": {
    "your-server": {
      "env": {
        "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN",
        "TELEGRAM_CHAT_ID": "YOUR_CHAT_ID"
      }
    }
  }
}
```

## Usage Examples

```
# Notify about completion
notify_telegram("Закончил работу над feature-auth. Создан PR #42", type="success")

# Ask a question
notify_telegram("Нужно уточнение: использовать REST или GraphQL?", type="question")

# Report error
notify_telegram("Ошибка: тесты не проходят в модуле auth", type="error")
```
