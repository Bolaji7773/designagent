# bot/telegram_bot.py
# Telegram bot — runs locally on your PC
# User sends messages from phone → agent processes → sends back preview

import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID
from agent.llm import ask_async


# ── Auth guard ───────────────────────────────────────────────
# If TELEGRAM_ALLOWED_USER_ID is set in .env, only that user
# can talk to the bot. Leave it blank to allow anyone.

def is_allowed(update: Update) -> bool:
    if not TELEGRAM_ALLOWED_USER_ID:
        return True
    return str(update.effective_user.id) == str(TELEGRAM_ALLOWED_USER_ID)


# ── Commands ─────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "👋 DesignAgent is running.\n\n"
        "Commands:\n"
        "/design  — create a design\n"
        "/status  — check what's configured\n"
        "/help    — show this message\n\n"
        "Or just send me an image with a caption describing what you want."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    from config.settings import get_available_providers, get_installed_apps
    providers = get_available_providers()
    apps      = get_installed_apps()

    provider_names = ", ".join(p["name"] for p in providers) if providers else "None"
    app_names      = ", ".join(a["name"] for a in apps)      if apps      else "None"

    await update.message.reply_text(
        f"── DesignAgent Status ──\n\n"
        f"🤖 AI Providers : {provider_names}\n"
        f"🎨 Design Apps  : {app_names}\n"
        f"🔒 Privacy Mode : On\n"
        f"📁 All files saved locally on your PC"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "── Commands ──\n\n"
        "/design  [prompt]  — run a design job\n"
        "/status            — check configured apps and providers\n"
        "/help              — show this message\n\n"
        "── Tips ──\n\n"
        "Send an image + caption to design with your own photo.\n"
        "Example: /design make a flyer for Afrobeats Night, Lagos, Saturday April 12"
    )


async def cmd_design(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text(
            "Tell me what to design.\n"
            "Example: /design make a party flyer for Club IV Lagos, Saturday 9pm"
        )
        return

    await update.message.reply_text("Got it. Working on it... 🎨")

    # For now — AI interprets the prompt and describes the design plan
    # Phase 1 completion: this will fire the actual design app driver
    try:
        result = await ask_async(
            prompt=prompt,
            system=(
                "You are an expert graphic designer AI assistant. "
                "The user wants you to design something. "
                "Describe clearly what you would create: layout, colors, "
                "typography, and key elements. Be specific and professional. "
                "Keep it under 200 words."
            )
        )
        await update.message.reply_text(f"🎨 Design plan:\n\n{result}\n\n"
                                        f"_(Driver execution coming in next build)_",
                                        parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Something went wrong: {e}")


# ── Image handler ─────────────────────────────────────────────
# User sends a photo with a caption

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    caption = update.message.caption or "No description provided"
    await update.message.reply_text(
        f"📷 Image received.\nCaption: {caption}\n\n"
        "Working on it... 🎨"
    )

    # Download image to uploads folder
    from config.settings import UPLOADS_FOLDER
    photo   = update.message.photo[-1]  # largest size
    file    = await context.bot.get_file(photo.file_id)
    save_path = UPLOADS_FOLDER / f"{photo.file_id}.jpg"
    await file.download_to_drive(str(save_path))

    # Ask AI to plan the design
    try:
        result = await ask_async(
            prompt=f"Design request: {caption}. An image has been provided as reference.",
            system=(
                "You are an expert graphic designer AI. "
                "The user sent an image and a design request. "
                "Describe the design you would create based on their request. "
                "Be specific about layout, colors, fonts, and elements. "
                "Keep it under 200 words."
            )
        )
        await update.message.reply_text(
            f"🎨 Design plan:\n\n{result}\n\n"
            f"_(Driver execution coming in next build)_",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Something went wrong: {e}")


# ── Start bot ─────────────────────────────────────────────────

async def start_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("design", cmd_design))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    print("  📱 Telegram bot listening...")

    # Initialize and start manually — avoids event loop conflict
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Keep running until cancelled
    await asyncio.Event().wait()

    # Clean shutdown
    await app.updater.stop()
    await app.stop()
    await app.shutdown()