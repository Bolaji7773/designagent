# main.py
# Run with: python main.py

import asyncio
import sys
from config.settings import (
    validate_config,
    get_available_providers,
    get_installed_apps,
    TELEGRAM_BOT_TOKEN,
    LOCAL_UI_PORT,
)

def print_banner():
    print("""
██████╗ ███████╗███████╗██╗ ██████╗ ███╗   ██╗
██╔══██╗██╔════╝██╔════╝██║██╔════╝ ████╗  ██║
██║  ██║█████╗  ███████╗██║██║  ███╗██╔██╗ ██║
██║  ██║██╔══╝  ╚════██║██║██║   ██║██║╚██╗██║
██████╔╝███████╗███████║██║╚██████╔╝██║ ╚████║
╚═════╝ ╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝

  Open-source AI design agent — v0.1.0
  Zero data stored. Bring your own API key.
    """)


def print_status():
    print("── Status ─────────────────────────────────────────")

    # Show configured AI providers
    providers = get_available_providers()
    if providers:
        names = ", ".join(p["name"] for p in providers)
        print(f"  ✅ AI Providers  : {names}")
    else:
        print("  ❌ AI Providers  : None — add a key to .env")

    # Show detected design apps
    apps = get_installed_apps()
    if apps:
        names = ", ".join(a["name"] for a in apps)
        print(f"  ✅ Design Apps   : {names}")
    else:
        print("  ⚠️  Design Apps   : None detected — add paths to .env")

    # Telegram status
    if TELEGRAM_BOT_TOKEN:
        print(f"  ✅ Telegram Bot  : Configured")
    else:
        print(f"  ⚠️  Telegram Bot  : Not configured — add token to .env")

    print(f"  🌐 Settings UI   : http://localhost:{LOCAL_UI_PORT}")

    # Any warnings
    warnings = validate_config()
    if warnings:
        print("\n── Warnings ───────────────────────────────────────")
        for w in warnings:
            print(f"  ⚠️  {w}")

    print("───────────────────────────────────────────────────\n")


async def main():
    print_banner()
    print_status()

    tasks = []

    # Start Telegram bot if token is configured
    if TELEGRAM_BOT_TOKEN:
        from bot.telegram_bot import start_bot
        print("  📱 Starting Telegram bot...")
        tasks.append(asyncio.create_task(start_bot()))
    else:
        print("  ℹ️  Telegram bot skipped — set TELEGRAM_BOT_TOKEN in .env\n")

    if not tasks:
        print("  ⚠️  Nothing to run — configure at least a Telegram token.")
        print("      Edit your .env file and run again.\n")
        return

    print("  DesignAgent is running. Press Ctrl+C to stop.\n")

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n  Shutting down. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())