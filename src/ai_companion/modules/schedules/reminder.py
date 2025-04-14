import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

DB_PATH = "reminders.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            reminder_text TEXT NOT NULL,
            reminder_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """
    )
    conn.commit()
    conn.close()

def add_reminder(chat_id: str, reminder_text: str, reminder_time: datetime):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO reminders (chat_id, reminder_text, reminder_time, status) VALUES (?, ?, ?, ?)",
        (chat_id, reminder_text, reminder_time.isoformat(), "pending"),
    )
    conn.commit()
    conn.close()

def get_due_reminders(window_minutes: int = 5) -> List[Tuple[int, str, str, str]]:
    now = datetime.now()
    window_start = now - timedelta(minutes=window_minutes)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, chat_id, reminder_text, reminder_time
        FROM reminders
        WHERE status = 'pending'
        AND reminder_time <= ?
        AND reminder_time > ?
        """,
        (now.isoformat(), window_start.isoformat()),
    )
    results = c.fetchall()
    conn.close()
    return results

def mark_reminder_sent(reminder_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET status = 'sent' WHERE id = ?",
        (reminder_id,),
    )
    conn.commit()
    conn.close()

def get_all_reminders(chat_id: str) -> List[Tuple[int, str, str, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, chat_id, reminder_text, reminder_time, status FROM reminders WHERE chat_id = ?",
        (chat_id,),
    )
    results = c.fetchall()
    conn.close()
    return results

# Initialize the database on import
init_db()
