import os
from dotenv import load_dotenv

load_dotenv()

_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

_DISPATCH = {
    "anthropic": "_anthropic_chat",
    "openai":    "_openai_chat",
    "groq":      "_groq_chat",
    "grok":      "_grok_chat",
    "gemini":    "_gemini_chat",
}


def chat(messages: list[dict], system: str = "", max_tokens: int = 1024) -> str:
    """Unified LLM call. Returns the assistant reply as a plain string.

    messages format (OpenAI-style): [{"role": "user", "content": "..."}]
    Switch provider by setting LLM_PROVIDER in .env — no code changes needed.
    Supported: anthropic | openai | groq | grok | gemini
    """
    fn_name = _DISPATCH.get(_PROVIDER)
    if not fn_name:
        raise ValueError(f"Unknown LLM_PROVIDER '{_PROVIDER}'. Choose: {list(_DISPATCH)}")
    return globals()[fn_name](messages, system, max_tokens)


# ── Anthropic ─────────────────────────────────────────────────────────────────

def _anthropic_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _openai_compatible_chat(
    messages: list[dict],
    system: str,
    max_tokens: int,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> str:
    from openai import OpenAI
    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    all_messages: list[dict] = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)
    resp = client.chat.completions.create(model=model, max_tokens=max_tokens, messages=all_messages)
    return resp.choices[0].message.content


def _openai_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    return _openai_compatible_chat(
        messages, system, max_tokens,
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
    )


# ── Groq ──────────────────────────────────────────────────────────────────────

def _groq_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    all_messages: list[dict] = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(messages)
    resp = client.chat.completions.create(model=model, max_tokens=max_tokens, messages=all_messages)
    return resp.choices[0].message.content


# ── Grok / xAI ───────────────────────────────────────────────────────────────

def _grok_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    return _openai_compatible_chat(
        messages, system, max_tokens,
        api_key=os.environ["GROK_API_KEY"],
        model=os.getenv("GROK_MODEL", "grok-2-latest"),
        base_url="https://api.x.ai/v1",
    )


# ── Gemini ────────────────────────────────────────────────────────────────────
# Uses google-genai>=1.0 — not the deprecated google-generativeai package.

def _gemini_chat(messages: list[dict], system: str, max_tokens: int) -> str:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    contents = [
        genai_types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[genai_types.Part(text=m["content"])],
        )
        for m in messages
    ]
    config = genai_types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        system_instruction=system or None,
    )
    resp = client.models.generate_content(model=model_name, contents=contents, config=config)
    return resp.text
