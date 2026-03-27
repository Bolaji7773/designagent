# agent/llm.py
# Universal AI interface — one function works for all providers
# Provider and model are read from .env — nothing hardcoded here

import os
import base64
from pathlib import Path
from litellm import completion, acompletion
from config.settings import DEFAULT_AI_PROVIDER, DEFAULT_MODEL, AI_PROVIDERS


def _build_kwargs(provider_id: str, model: str, messages: list, **kwargs) -> dict:
    """
    Builds the correct arguments for whichever provider is being used.
    Each provider needs slightly different setup — this handles all of them.
    """
    provider = AI_PROVIDERS.get(provider_id, AI_PROVIDERS["groq"])

    call_kwargs = {
        "model": model,
        "messages": messages,
        **kwargs,
    }

    # Inject API key if this provider needs one
    api_key = provider.get("api_key")
    if provider.get("requires_key") and api_key:
        call_kwargs["api_key"] = api_key

    # Ollama runs locally — needs a base URL instead of an API key
    if provider_id == "ollama":
        call_kwargs["api_base"] = provider.get("host", "http://localhost:11434")

    # OpenRouter needs to know who is calling it
    if provider_id == "openrouter":
        call_kwargs["headers"] = {
            "HTTP-Referer": "https://github.com/yourusername/designagent",
            "X-Title": "DesignAgent",
        }

    return call_kwargs


def _build_messages(prompt: str, system: str = None, images: list = None) -> list:
    """
    Builds the messages list.
    Handles plain text prompts and image+text prompts for vision tasks.
    """
    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    # Vision request — attach images alongside the prompt
    if images:
        content = [{"type": "text", "text": prompt}]

        for img_path in images:
            img_bytes = Path(img_path).read_bytes()
            img_b64   = base64.b64encode(img_bytes).decode()
            ext       = Path(img_path).suffix.lower().strip(".")
            mime_map  = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }
            mime = mime_map.get(ext, "image/png")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{img_b64}"}
            })

        messages.append({"role": "user", "content": content})

    # Plain text request
    else:
        messages.append({"role": "user", "content": prompt})

    return messages


def ask(
    prompt: str,
    system: str = None,
    provider: str = None,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    images: list = None,
) -> str:
    """
    Synchronous AI call. Returns response as a string.

    Args:
        prompt      : What you want the AI to do
        system      : Optional instructions that shape how the AI behaves
        provider    : Override provider (default: from .env)
        model       : Override model (default: from .env)
        temperature : 0.0 = focused/deterministic, 1.0 = creative
        max_tokens  : Max length of response
        images      : List of local image file paths (for vision tasks)

    Example:
        result = ask("Write a flyer headline for a Lagos night party")
        result = ask("What is in this image?", images=["./photo.png"])
    """
    provider_id = provider or DEFAULT_AI_PROVIDER
    model_id    = model    or DEFAULT_MODEL

    messages = _build_messages(prompt, system, images)
    kwargs   = _build_kwargs(
        provider_id, model_id, messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response = completion(**kwargs)
    return response.choices[0].message.content


async def ask_async(
    prompt: str,
    system: str = None,
    provider: str = None,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    images: list = None,
) -> str:
    """
    Async version of ask().
    Use this inside the Telegram bot and FastAPI server.
    Everything else is identical to ask().
    """
    provider_id = provider or DEFAULT_AI_PROVIDER
    model_id    = model    or DEFAULT_MODEL

    messages = _build_messages(prompt, system, images)
    kwargs   = _build_kwargs(
        provider_id, model_id, messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response = await acompletion(**kwargs)
    return response.choices[0].message.content


async def ask_with_fallback(
    prompt: str,
    system: str = None,
    fallback_chain: list = None,
    **kwargs,
) -> str:
    """
    Tries providers in order. If one fails it moves to the next.
    This means the agent never crashes just because one provider
    is down or rate-limited.

    Default fallback order:
      your configured provider → groq → gemini → ollama

    Example:
        result = await ask_with_fallback(
            prompt="Design a flyer",
            fallback_chain=["claude", "groq", "ollama"]
        )
    """
    chain = fallback_chain or [DEFAULT_AI_PROVIDER, "groq", "gemini", "ollama"]

    # Remove duplicates, keep order
    seen  = set()
    chain = [x for x in chain if not (x in seen or seen.add(x))]

    last_error = None

    for provider_id in chain:
        provider = AI_PROVIDERS.get(provider_id)
        if not provider:
            continue

        # Skip providers that need a key but don't have one
        if provider.get("requires_key") and not provider.get("api_key"):
            print(f"[LLM] Skipping {provider_id} — no API key configured")
            continue

        try:
            model  = provider.get("default_model")
            result = await ask_async(
                prompt=prompt,
                system=system,
                provider=provider_id,
                model=model,
                **kwargs,
            )
            print(f"[LLM] Used provider: {provider_id}")
            return result

        except Exception as e:
            last_error = e
            print(f"[LLM] {provider_id} failed: {e} — trying next provider")
            continue

    raise RuntimeError(f"All providers failed. Last error: {last_error}")