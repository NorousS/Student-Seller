#!/usr/bin/env python3
"""
Agent communication helper - ask questions and get answers via Telegram.

Usage:
    python tg_ask.py "Какую базу данных использовать: PostgreSQL или MySQL?"
    python tg_ask.py "Продолжить рефакторинг?" --timeout 300

The script will:
1. Send the question to Telegram
2. Wait for your reply
3. Print your answer to stdout (for agent to use)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse


def send_message(token: str, chat_id: str, text: str) -> bool:
    """Send a message to Telegram."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            return result.get("ok", False)
    except Exception as e:
        print(f"Error sending: {e}", file=sys.stderr)
        return False


def get_updates(token: str, offset: int = 0, timeout: int = 30) -> list:
    """Get updates from Telegram."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = urllib.parse.urlencode({
        "offset": offset,
        "timeout": timeout,
        "allowed_updates": json.dumps(["message"])
    })
    
    try:
        req = urllib.request.Request(f"{url}?{params}")
        with urllib.request.urlopen(req, timeout=timeout + 10) as response:
            result = json.loads(response.read().decode())
            if result.get("ok"):
                return result.get("result", [])
    except Exception:
        pass
    return []


def ask_and_wait(token: str, chat_id: str, question: str, timeout: int = 120) -> str | None:
    """Send question and wait for answer."""
    
    # Clear old updates and get current offset
    updates = get_updates(token, timeout=0)
    offset = updates[-1]["update_id"] + 1 if updates else 0
    
    # Send question
    full_question = f"❓ <b>Agent Question</b>\n\n{question}\n\n<i>Reply to this message...</i>"
    if not send_message(token, chat_id, full_question):
        print("Failed to send question", file=sys.stderr)
        return None
    
    print(f"Question sent, waiting for reply (timeout: {timeout}s)...", file=sys.stderr)
    
    # Wait for answer
    start_time = time.time()
    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        updates = get_updates(token, offset=offset, timeout=min(30, remaining))
        
        for update in updates:
            offset = update["update_id"] + 1
            
            message = update.get("message", {})
            msg_chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")
            
            if msg_chat_id == chat_id and text:
                # Send confirmation
                send_message(token, chat_id, f"✅ Got it: {text[:50]}{'...' if len(text) > 50 else ''}")
                return text
    
    send_message(token, chat_id, "⏰ Timeout - no response received")
    return None


def main():
    parser = argparse.ArgumentParser(description="Ask a question via Telegram and wait for answer")
    parser.add_argument("question", help="Question to ask")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds (default: 120)")
    
    args = parser.parse_args()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set", file=sys.stderr)
        sys.exit(1)
    
    answer = ask_and_wait(token, chat_id, args.question, args.timeout)
    
    if answer:
        print(answer)
        sys.exit(0)
    else:
        print("No answer received", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
