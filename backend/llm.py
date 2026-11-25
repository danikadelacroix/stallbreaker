"""The one place a language model is called.

A model is used only to read messy notes (see intake.py). It never chooses a source, a schedule
or a time in the plan. With no key, or on any failure, reader() or the call returns None and the
caller falls back to plain rules and says so.

Set-up: put OPENROUTER_API_KEY and LLM_MODEL in a .env file in the repo root (it is git-ignored).
"""
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://openrouter.ai/api/v1/chat/completions"  # fixed here on purpose: no base-URL setting from the environment is used
TIMEOUT_SECONDS = 5


def _load_env():
    """Read KEY=VALUE lines from .env, without overriding what is already set."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env()


class _OpenRouter:
    """Asks one model for one JSON answer. Any problem at all gives None."""

    def __init__(self, key, model):
        self._key, self.name = key, model

    def __call__(self, system, user, schema):
        body = {"model": self.name,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "response_format": {"type": "json_schema", "json_schema": {"name": "reading", "strict": True, "schema": schema}}}
        request = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                         headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                answer = json.load(response)["choices"][0]["message"]["content"]
            return json.loads(answer)
        except Exception:  # no network, timeout, refusal, bad JSON: all mean "no answer"
            return None


def reader():
    """A callable ask(system, user, schema) -> dict or None, or None when no model is set up."""
    key, model = os.environ.get("OPENROUTER_API_KEY"), os.environ.get("LLM_MODEL")
    return _OpenRouter(key, model) if key and model else None


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_VIN = re.compile(r"\b(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])(?=[A-HJ-NPR-Z0-9]*\d)[A-HJ-NPR-Z0-9]{17}\b")
_PHONE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b|\b[6-9]\d{9}\b")


def redact(text):
    """Remove email addresses, vehicle identification numbers and phone numbers before a note leaves the machine."""
    text = _EMAIL.sub("[email]", text)
    text = _VIN.sub("[vin]", text)
    return _PHONE.sub("[phone]", text)
