#!/usr/bin/env python3
"""
Check Telegram for new messages and return them.

Usage:
    python check_telegram.py                    # Check once
    python check_telegram.py --last 5           # Get last 5 messages
    python check_telegram.py --unread-only      # Only unread messages
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta


def get_updates(token: str, offset: int = None, limit: int = 5) -> list:
    """Get updates from Telegram."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"limit": limit}
    if offset is not None:
        params["offset"] = offset
    
    query_string = urllib.parse.urlencode(params)
    
    try:
        req = urllib.request.Request(f"{url}?{query_string}")
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if result.get("ok"):
                return result.get("result", [])
    except Exception as e:
        print(f"Error fetching updates: {e}", file=sys.stderr)
    
    return []


def format_message(update: dict) -> dict:
    """Format Telegram update into readable structure."""
    message = update.get("message", {})
    return {
        "update_id": update.get("update_id"),
        "message_id": message.get("message_id"),
        "from_user": message.get("from", {}).get("username", "unknown"),
        "chat_id": message.get("chat", {}).get("id"),
        "text": message.get("text", ""),
        "date": datetime.fromtimestamp(message.get("date", 0)).isoformat(),
        "raw_date": message.get("date", 0)
    }


def get_last_messages(token: str, chat_id: str, count: int = 5, unread_only: bool = False) -> list:
    """Get last N messages from Telegram."""
    updates = get_updates(token, limit=count)
    
    messages = []
    for update in updates:
        msg = format_message(update)
        
        # Filter by chat_id
        if str(msg["chat_id"]) != str(chat_id):
            continue
        
        # Skip empty messages
        if not msg["text"]:
            continue
        
        messages.append(msg)
    
    return messages


def mark_as_read(token: str, offset: int):
    """Mark messages as read by confirming offset."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = urllib.parse.urlencode({"offset": offset})
    
    try:
        req = urllib.request.Request(f"{url}?{params}")
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode())
            return result.get("ok", False)
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Check Telegram messages")
    parser.add_argument("--last", type=int, default=5, help="Number of last messages to retrieve")
    parser.add_argument("--unread-only", action="store_true", help="Only unread messages")
    parser.add_argument("--mark-read", action="store_true", help="Mark messages as read after retrieval")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    if not chat_id:
        print("Error: TELEGRAM_CHAT_ID not set", file=sys.stderr)
        sys.exit(1)
    
    messages = get_last_messages(token, chat_id, args.last, args.unread_only)
    
    if not messages:
        if not args.json:
            print("No new messages", file=sys.stderr)
        else:
            print(json.dumps({"messages": []}, ensure_ascii=False))
        sys.exit(0)
    
    if args.json:
        print(json.dumps({"messages": messages}, ensure_ascii=False, indent=2))
    else:
        print(f"📬 Found {len(messages)} message(s):\n")
        for msg in messages:
            print(f"[{msg['date']}] @{msg['from_user']}: {msg['text']}")
            print()
    
    # Mark as read if requested
    if args.mark_read and messages:
        last_update_id = messages[-1]["update_id"]
        mark_as_read(token, last_update_id + 1)
        if not args.json:
            print("✓ Marked as read", file=sys.stderr)


if __name__ == "__main__":
    main()
