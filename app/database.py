from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.config import settings


DB_PATH = settings.database_path


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TEXT NOT NULL,
                total_messages INTEGER DEFAULT 0,
                total_dialogs INTEGER DEFAULT 0,
                selected_model TEXT,
                language TEXT DEFAULT 'ru',
                memory_enabled INTEGER DEFAULT 1,
                notifications_enabled INTEGER DEFAULT 1,
                persona TEXT DEFAULT 'friendly and practical',
                active_dialog_id INTEGER DEFAULT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS dialogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model TEXT,
                active INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dialog_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                model TEXT,
                FOREIGN KEY (dialog_id) REFERENCES dialogs(id) ON DELETE CASCADE
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_dialogs_user_id ON dialogs(user_id)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_dialog_id ON messages(dialog_id)"
        )
        await db.commit()


async def get_connection() -> aiosqlite.Connection:
    return await aiosqlite.connect(DB_PATH)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def ensure_user(user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        user = await row.fetchone()
        if not user:
            await db.execute(
                """
                INSERT INTO users (
                    user_id, username, first_name, last_name, registered_at,
                    selected_model, language, memory_enabled, notifications_enabled, persona
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    first_name,
                    last_name,
                    utc_now(),
                    settings.default_model,
                    "ru",
                    1,
                    1,
                    "friendly and practical",
                ),
            )
            await db.commit()
            user = await (await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))).fetchone()
    if user is None:
        return {}
    return {
        "user_id": user[0],
        "username": user[1],
        "first_name": user[2],
        "last_name": user[3],
        "registered_at": user[4],
        "total_messages": user[5],
        "total_dialogs": user[6],
        "selected_model": user[7],
        "language": user[8],
        "memory_enabled": bool(user[9]),
        "notifications_enabled": bool(user[10]),
        "persona": user[11],
        "active_dialog_id": user[12],
    }


async def get_user(user_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await row.fetchone()
        if user is None:
            return None
        return {
            "user_id": user[0],
            "username": user[1],
            "first_name": user[2],
            "last_name": user[3],
            "registered_at": user[4],
            "total_messages": user[5],
            "total_dialogs": user[6],
            "selected_model": user[7],
            "language": user[8],
            "memory_enabled": bool(user[9]),
            "notifications_enabled": bool(user[10]),
            "persona": user[11],
            "active_dialog_id": user[12],
        }


async def set_user_field(user_id: int, field_name: str, value: Any) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field_name} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def get_or_create_active_dialog(user_id: int, model: str | None = None) -> int:
    user = await get_user(user_id)
    if user and user["active_dialog_id"]:
        return user["active_dialog_id"]
    return await create_dialog(user_id, title=f"Диалог #{(await get_user_total_dialogs(user_id)) + 1}", model=model)


async def create_dialog(user_id: int, title: str | None = None, model: str | None = None) -> int:
    now = utc_now()
    if not title:
        count = await get_user_total_dialogs(user_id)
        title = f"Диалог #{count + 1}"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO dialogs (user_id, title, created_at, updated_at, model, active) VALUES (?, ?, ?, ?, ?, 1)",
            (user_id, title, now, now, model or ""),
        )
        dialog_id = cursor.lastrowid
        await db.execute("UPDATE users SET total_dialogs = total_dialogs + 1, active_dialog_id = ? WHERE user_id = ?", (dialog_id, user_id))
        await db.execute("UPDATE dialogs SET active = 0 WHERE user_id = ? AND id != ?", (user_id, dialog_id))
        await db.commit()
    return dialog_id


async def get_user_total_dialogs(user_id: int) -> int:
    user = await get_user(user_id)
    return user["total_dialogs"] if user else 0


async def get_user_dialogs(user_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute(
            "SELECT * FROM dialogs WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        dialogs = await rows.fetchall()
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "model": row[5],
            "active": bool(row[6]),
        }
        for row in dialogs
    ]


async def get_active_dialog(user_id: int) -> dict[str, Any] | None:
    user = await get_user(user_id)
    if not user or not user["active_dialog_id"]:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT * FROM dialogs WHERE id = ?", (user["active_dialog_id"],))).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "user_id": row[1],
        "title": row[2],
        "created_at": row[3],
        "updated_at": row[4],
        "model": row[5],
        "active": bool(row[6]),
    }


async def set_active_dialog(user_id: int, dialog_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE dialogs SET active = 0 WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE dialogs SET active = 1 WHERE id = ? AND user_id = ?", (dialog_id, user_id))
        await db.execute("UPDATE users SET active_dialog_id = ? WHERE user_id = ?", (dialog_id, user_id))
        await db.commit()


async def delete_dialog(dialog_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE dialog_id = ?", (dialog_id,))
        await db.execute("DELETE FROM dialogs WHERE id = ? AND user_id = ?", (dialog_id, user_id))
        await db.execute("UPDATE users SET total_dialogs = total_dialogs - 1 WHERE user_id = ?", (user_id,))
        remaining = await (await db.execute("SELECT id FROM dialogs WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user_id,))).fetchone()
        if remaining:
            await db.execute("UPDATE users SET active_dialog_id = ? WHERE user_id = ?", (remaining[0], user_id))
        else:
            await db.execute("UPDATE users SET active_dialog_id = NULL WHERE user_id = ?", (user_id,))
        await db.commit()


async def save_message(dialog_id: int, role: str, content: str, model: str | None = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (dialog_id, role, content, created_at, model) VALUES (?, ?, ?, ?, ?)",
            (dialog_id, role, content, utc_now(), model),
        )
        await db.execute("UPDATE dialogs SET updated_at = ? WHERE id = ?", (utc_now(), dialog_id))
        await db.execute("UPDATE users SET total_messages = total_messages + 1 WHERE user_id = (SELECT user_id FROM dialogs WHERE id = ?)", (dialog_id,))
        await db.commit()


async def get_dialog_messages(dialog_id: int, limit: int = 12) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute(
            "SELECT role, content, model FROM messages WHERE dialog_id = ? ORDER BY id DESC LIMIT ?",
            (dialog_id, limit * 2),
        )
        messages = await rows.fetchall()
    ordered = reversed(messages)
    return [{"role": row[0], "content": row[1], "model": row[2]} for row in ordered]


async def clear_dialog_context(dialog_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE dialog_id = ?", (dialog_id,))
        await db.execute("UPDATE dialogs SET updated_at = ? WHERE id = ?", (utc_now(), dialog_id))
        await db.commit()


async def get_admin_stats() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        users_count = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        dialogs_count = await (await db.execute("SELECT COUNT(*) FROM dialogs")).fetchone()
        messages_count = await (await db.execute("SELECT COUNT(*) FROM messages")).fetchone()
    return {
        "users": users_count[0],
        "dialogs": dialogs_count[0],
        "messages": messages_count[0],
    }


async def get_user_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await db.execute(
            "SELECT id, title, created_at, updated_at, model FROM dialogs WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        )
        dialogs = await rows.fetchall()
    return [
        {"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3], "model": row[4]}
        for row in dialogs
    ]
