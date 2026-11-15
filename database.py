from __future__ import annotations

import time

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    exclude_words TEXT NOT NULL DEFAULT '',
                    interval_min INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    initialized INTEGER NOT NULL DEFAULT 0,
                    next_check REAL NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS seen_links (
                    search_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    PRIMARY KEY (search_id, url),
                    FOREIGN KEY (search_id) REFERENCES searches(id) ON DELETE CASCADE
                );
                """
            )
            await db.commit()

    async def add_search(self, chat_id: int, name: str, url: str, exclude: str, interval: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO searches(chat_id,name,url,exclude_words,interval_min,next_check) VALUES(?,?,?,?,?,?)",
                (chat_id, name, url, exclude, interval, time.time()),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_searches(self, chat_id: int):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM searches WHERE chat_id=? ORDER BY id", (chat_id,))
            return await cursor.fetchall()

    async def due_searches(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM searches WHERE active=1 AND next_check<=? ORDER BY next_check", (time.time(),)
            )
            return await cursor.fetchall()

    async def seen(self, search_id: int, urls: list[str]) -> set[str]:
        if not urls:
            return set()
        placeholders = ",".join("?" for _ in urls)
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                f"SELECT url FROM seen_links WHERE search_id=? AND url IN ({placeholders})", (search_id, *urls)
            )
            return {row[0] for row in await cursor.fetchall()}

    async def add_seen(self, search_id: int, urls: list[str]) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executemany(
                "INSERT OR IGNORE INTO seen_links(search_id,url) VALUES(?,?)", ((search_id, url) for url in urls)
            )
            await db.commit()

    async def mark_checked(self, search_id: int, interval: int, initialized: bool = True) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE searches SET next_check=?, initialized=? WHERE id=?",
                (time.time() + interval * 60, int(initialized), search_id),
            )
            await db.commit()

    async def delete_search(self, search_id: int, chat_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("DELETE FROM searches WHERE id=? AND chat_id=?", (search_id, chat_id))
            await db.commit()
            return cursor.rowcount > 0


