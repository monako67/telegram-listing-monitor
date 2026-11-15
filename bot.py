from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlsplit

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import Config, load_config
from database import Database
from scraper import fetch_items

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def allowed(update: Update, config: Config) -> bool:
    user = update.effective_user
    return user is not None and (not config.allowed_user_ids or user.id in config.allowed_user_ids)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not allowed(update, context.application.bot_data["config"]):
        await update.effective_message.reply_text("Access denied.")
        return
    await update.effective_message.reply_text(
        "I monitor search pages and notify you about new links.\n\n"
        "/add name | https://site/search | excluded words\n"
        "/list - show searches\n/delete ID - remove a search"
    )


async def add_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if not allowed(update, config):
        await update.effective_message.reply_text("Access denied.")
        return
    parts = " ".join(context.args).split("|", maxsplit=2)
    if len(parts) < 2:
        await update.effective_message.reply_text("Usage: /add name | https://site/search | excluded words")
        return
    name, url = parts[0].strip(), parts[1].strip()
    parsed = urlsplit(url)
    if not name or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        await update.effective_message.reply_text("Provide a name and a valid HTTP/HTTPS URL.")
        return
    excluded = parts[2].strip() if len(parts) == 3 else ""
    db: Database = context.application.bot_data["db"]
    search_id = await db.add_search(
        update.effective_chat.id, name[:100], url, excluded, config.default_interval_minutes
    )
    await update.effective_message.reply_text(f"Search #{search_id} added. Initial results will be remembered.")


async def list_searches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if not allowed(update, config):
        await update.effective_message.reply_text("Access denied.")
        return
    rows = await context.application.bot_data["db"].list_searches(update.effective_chat.id)
    text = "\n\n".join(f"#{row['id']} {row['name']}\n{row['url']}" for row in rows) or "No searches yet."
    await update.effective_message.reply_text(text)


async def delete_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if not allowed(update, config):
        await update.effective_message.reply_text("Access denied.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.effective_message.reply_text("Usage: /delete ID")
        return
    deleted = await context.application.bot_data["db"].delete_search(
        int(context.args[0]), update.effective_chat.id
    )
    await update.effective_message.reply_text("Deleted." if deleted else "Search not found.")


async def check_search(application: Application, row) -> None:
    config: Config = application.bot_data["config"]
    db: Database = application.bot_data["db"]
    items = await fetch_items(row["url"], config.max_links_per_check, config.user_agent)
    urls = [url for url, _ in items]
    known = await db.seen(row["id"], urls)
    unseen = [(url, title) for url, title in items if url not in known]
    excluded = {word.casefold() for word in row["exclude_words"].replace(",", " ").split()}
    relevant = [item for item in unseen if not any(word in item[1].casefold() for word in excluded)]

    if row["initialized"] and relevant:
        message = f"New links for {row['name']}:\n\n" + "\n\n".join(
            f" {title}\n{url}" for url, title in relevant
        )
        await application.bot.send_message(row["chat_id"], message[:4000])
    await db.add_seen(row["id"], [url for url, _ in unseen])
    await db.mark_checked(row["id"], row["interval_min"])


async def worker(application: Application) -> None:
    while True:
        for row in await application.bot_data["db"].due_searches():
            try:
                await check_search(application, row)
            except Exception:
                logger.exception("Search %s failed", row["id"])
                await application.bot_data["db"].mark_checked(row["id"], row["interval_min"], bool(row["initialized"]))
        await asyncio.sleep(15)


async def post_init(application: Application) -> None:
    await application.bot_data["db"].initialize()
    application.bot_data["worker"] = asyncio.create_task(worker(application))


def main() -> None:
    config = load_config()
    app = Application.builder().token(config.bot_token).post_init(post_init).build()
    app.bot_data.update(config=config, db=Database(config.database_path))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_search))
    app.add_handler(CommandHandler("list", list_searches))
    app.add_handler(CommandHandler("delete", delete_search))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()


