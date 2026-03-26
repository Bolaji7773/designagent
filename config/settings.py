# config/settings.py
# Reads everything from .env
# Every other file imports from here — nothing hardcoded

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# ── AI Providers ────────────────────────────────────────────

AI_PROVIDERS = {
    "groq": {
        "name": "Groq",
        "api_key": os.getenv("GROQ_API_KEY"),
        "models": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
            "groq/mixtral-8x7b-32768",
        ],
        "default_model": "groq/llama-3.3-70b-versatile",
        "requires_key": True,
        "free_tier": True,
        "docs": "https://console.groq.com",
    },
    "claude": {
        "name": "Anthropic Claude",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
        "default_model": "claude-3-5-sonnet-20241022",
        "requires_key": True,
        "free_tier": False,
        "docs": "https://console.anthropic.com",
    },
    "gemini": {
        "name": "Google Gemini",
        "api_key": os.getenv("GEMINI_API_KEY"),
        "models": [
            "gemini/gemini-2.0-flash",
            "gemini/gemini-1.5-pro",
        ],
        "default_model": "gemini/gemini-2.0-flash",
        "requires_key": True,
        "free_tier": True,
        "docs": "https://aistudio.google.com/app/apikey",
    },
    "openai": {
        "name": "OpenAI",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "default_model": "gpt-4o-mini",
        "requires_key": True,
        "free_tier": False,
        "docs": "https://platform.openai.com/api-keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "models": [
            "openrouter/meta-llama/llama-3.3-70b",
            "openrouter/google/gemini-2.0-flash-exp:free",
        ],
        "default_model": "openrouter/meta-llama/llama-3.3-70b",
        "requires_key": True,
        "free_tier": True,
        "docs": "https://openrouter.ai/keys",
    },
    "ollama": {
        "name": "Ollama (Offline)",
        "api_key": None,
        "models": [
            "ollama/llama3.3",
            "ollama/mistral",
            "ollama/phi3",
        ],
        "default_model": "ollama/llama3.3",
        "requires_key": False,
        "free_tier": True,
        "docs": "https://ollama.com",
        "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    },
}

# Active provider — comes from .env
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "groq")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "groq/llama-3.3-70b-versatile")

# ── Telegram ─────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")

# ── Design App Paths ─────────────────────────────────────────

DESIGN_APPS = {
    "photoshop": {
        "name": "Adobe Photoshop",
        "path": os.getenv("PHOTOSHOP_PATH"),
        "paid": True,
        "platform": ["windows", "mac"],
    },
    "coreldraw": {
        "name": "CorelDRAW",
        "path": os.getenv("CORELDRAW_PATH"),
        "paid": True,
        "platform": ["windows"],
    },
    "gimp": {
        "name": "GIMP (Free)",
        "path": os.getenv("GIMP_PATH"),
        "paid": False,
        "platform": ["windows", "mac", "linux"],
    },
    "inkscape": {
        "name": "Inkscape (Free)",
        "path": os.getenv("INKSCAPE_PATH"),
        "paid": False,
        "platform": ["windows", "mac", "linux"],
    },
    "krita": {
        "name": "Krita (Free)",
        "path": os.getenv("KRITA_PATH"),
        "paid": False,
        "platform": ["windows", "mac", "linux"],
    },
    "figma": {
        "name": "Figma",
        "path": None,
        "access_token": os.getenv("FIGMA_ACCESS_TOKEN"),
        "paid": False,
        "platform": ["web"],
    },
}

# ── Local Storage ─────────────────────────────────────────────

OUTPUT_FOLDER          = Path(os.getenv("OUTPUT_FOLDER",          "./output/designs"))
SHOWCASE_OUTPUT_FOLDER = Path(os.getenv("SHOWCASE_OUTPUT_FOLDER", "./output/showcase"))
UPLOADS_FOLDER         = Path(os.getenv("UPLOADS_FOLDER",         "./output/uploads"))
BRAND_KIT_FOLDER       = Path(os.getenv("BRAND_KIT_FOLDER",       "./config/brand_kit"))
DATABASE_PATH          = Path(os.getenv("DATABASE_PATH",           "./config/agent.db"))

# Create folders if they don't exist yet
for _folder in [OUTPUT_FOLDER, SHOWCASE_OUTPUT_FOLDER, UPLOADS_FOLDER, BRAND_KIT_FOLDER]:
    _folder.mkdir(parents=True, exist_ok=True)

# ── Local UI ──────────────────────────────────────────────────

LOCAL_UI_PORT = int(os.getenv("LOCAL_UI_PORT", 3000))

# ── Privacy ───────────────────────────────────────────────────

PRIVACY_MODE               = os.getenv("PRIVACY_MODE", "true").lower() == "true"
AUTO_DELETE_HISTORY_DAYS   = int(os.getenv("AUTO_DELETE_HISTORY_DAYS", 0))

# ── Helper Functions ──────────────────────────────────────────

def get_available_providers():
    """Returns only providers that have a key set (or don't need one)."""
    available = []
    for key, p in AI_PROVIDERS.items():
        has_key = bool(p.get("api_key"))
        no_key_needed = not p.get("requires_key")
        if has_key or no_key_needed:
            available.append({"id": key, **p})
    return available


def get_installed_apps():
    """Returns only design apps detected on this machine."""
    installed = []
    for key, app in DESIGN_APPS.items():
        path  = app.get("path")
        token = app.get("access_token")
        # Web apps just need a token
        if app["platform"] == ["web"] and token:
            installed.append({"id": key, **app})
        # Local apps need a valid path that actually exists
        elif path and Path(path).exists():
            installed.append({"id": key, **app})
    return installed


def validate_config():
    """Checks config on startup. Returns list of warning strings."""
    warnings = []

    if not TELEGRAM_BOT_TOKEN:
        warnings.append(
            "TELEGRAM_BOT_TOKEN not set — Telegram bot will not start"
        )

    active = AI_PROVIDERS.get(DEFAULT_AI_PROVIDER, {})
    if active.get("requires_key") and not active.get("api_key"):
        warnings.append(
            f"No API key for {active.get('name', DEFAULT_AI_PROVIDER)} "
            f"— add {DEFAULT_AI_PROVIDER.upper()}_API_KEY to .env"
        )

    if not get_installed_apps():
        warnings.append(
            "No design apps detected — add app paths to .env"
        )

    return warnings