#!/usr/bin/env python3
"""
Telegram notification script for agent work updates.

Usage:
    python tg_notify.py "Your message" [--type info|question|success|error|warning]

Environment variables required:
    TELEGRAM_BOT_TOKEN - Bot token from @BotFather
    TELEGRAM_CHAT_ID   - Your chat ID from @userinfobot
"""

import argparse
import os
import sys
import urllib.request
import urllib.parse
import json


def send_telegram(message: str, msg_type: str = "info") -> bool:
    """Send notification to Telegram."""
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        return False
    
    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID not set", file=sys.stderr)
        return False
    
    emoji_map = {
        "info": "ℹ️",
        "question": "❓",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "start": "🚀",
        "done": "🎉",
    }
    emoji = emoji_map.get(msg_type, "📢")
    
    full_message = f"{emoji} <b>Agent Update</b>\n\n{message}"
    
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
                print("✓ Message sent")
                return True
            else:
                print(f"Error: {result.get('description')}", file=sys.stderr)
                return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Telegram notification")
    parser.add_argument("message", help="Message to send")
    parser.add_argument(
        "--type", "-t",
        choices=["info", "question", "success", "error", "warning", "start", "done"],
        default="info",
        help="Message type (affects emoji)"
    )
    
    args = parser.parse_args()
    success = send_telegram(args.message, args.type)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
