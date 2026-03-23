#!/usr/bin/env python3
"""
Telegram command listener for agent communication.

Listens for messages from Telegram and outputs them to stdout.
Can be used by agents to receive commands/feedback from user.

Usage:
    python tg_listener.py              # Wait for one message
    python tg_listener.py --poll       # Continuous polling
    python tg_listener.py --timeout 60 # Wait up to 60 seconds

Environment variables required:
    TELEGRAM_BOT_TOKEN - Bot token from @BotFather
    TELEGRAM_CHAT_ID   - Your chat ID (only messages from this ID are processed)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse


def get_updates(token: str, offset: int = 0, timeout: int = 30) -> list:
    """Get updates from Telegram using long polling."""
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
    except Exception as e:
        print(f"Error fetching updates: {e}", file=sys.stderr)
    
    return []


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
    except Exception:
        return False


def listen_once(token: str, allowed_chat_id: str, timeout: int = 60) -> str | None:
    """Wait for a single message and return it."""
    print(f"⏳ Waiting for message (timeout: {timeout}s)...", file=sys.stderr)
    
    # Get current update_id to ignore old messages
    updates = get_updates(token, timeout=0)
    offset = updates[-1]["update_id"] + 1 if updates else 0
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        updates = get_updates(token, offset=offset, timeout=min(30, timeout))
        
        for update in updates:
            offset = update["update_id"] + 1
            
            message = update.get("message", {})
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")
            
            # Only process messages from allowed chat
            if chat_id == allowed_chat_id and text:
                # Send acknowledgment
                send_message(token, chat_id, f"✓ Получено: {text[:50]}...")
                return text
    
    return None


def poll_continuous(token: str, allowed_chat_id: str):
    """Continuously poll for messages and print them."""
    print("🔄 Starting continuous polling (Ctrl+C to stop)...", file=sys.stderr)
    
    # Get current update_id
    updates = get_updates(token, timeout=0)
    offset = updates[-1]["update_id"] + 1 if updates else 0
    
    send_message(token, allowed_chat_id, "🤖 Agent listener started. Send commands here.")
    
    try:
        while True:
            updates = get_updates(token, offset=offset, timeout=30)
            
            for update in updates:
                offset = update["update_id"] + 1
                
                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id", ""))
                text = message.get("text", "")
                username = message.get("from", {}).get("username", "unknown")
                
                if chat_id == allowed_chat_id and text:
                    # Output message as JSON for parsing
                    output = {
                        "text": text,
                        "username": username,
                        "timestamp": message.get("date"),
                        "message_id": message.get("message_id")
                    }
                    print(json.dumps(output, ensure_ascii=False))
                    sys.stdout.flush()
                    
                    # Acknowledge
                    send_message(token, chat_id, f"✓ Received: {text[:30]}...")
                    
    except KeyboardInterrupt:
        print("\n👋 Polling stopped.", file=sys.stderr)
        send_message(token, allowed_chat_id, "👋 Agent listener stopped.")


def main():
    parser = argparse.ArgumentParser(description="Listen for Telegram commands")
    parser.add_argument("--poll", action="store_true", help="Continuous polling mode")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    
    args = parser.parse_args()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID not set", file=sys.stderr)
        sys.exit(1)
    
    if args.poll:
        poll_continuous(token, chat_id)
    else:
        message = listen_once(token, chat_id, args.timeout)
        if message:
            print(message)
        else:
            print("No message received within timeout", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
