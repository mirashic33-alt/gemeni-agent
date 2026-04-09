"""
provider.py — Google Gemini client (new SDK: google-genai).

IMPORTANT: use `from google import genai`, NOT `google-generativeai`.
"""

from google import genai
from google.genai import types

from data.logger import get_logger

log = get_logger("llm")

MODEL = "gemini-3-flash-preview"


class GeminiProvider:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self.client: genai.Client | None = None
        self.model: str = MODEL
        self._chat = None          # active chat session
        self._system_prompt = ""   # system prompt loaded from file

    def connect(self) -> None:
        log.info("Initializing Gemini client...")
        self.client = genai.Client(api_key=self._api_key)
        log.info("Gemini client created.")

    def ping(self) -> bool:
        if self.client is None:
            raise RuntimeError("Client not initialized.")
        log.info(f"Pinging model {MODEL}...")
        response = self.client.models.generate_content(
            model=MODEL,
            contents="Say: ok",
            config=types.GenerateContentConfig(max_output_tokens=8),
        )
        ok = bool(response.candidates)
        log.info(f"Ping {'ok' if ok else 'failed'}.")
        return ok

    def start_chat(self, history: list[dict] | None = None, system_prompt: str = "") -> None:
        """
        Creates a chat session.
        history — list of {"role": "user"|"agent", "text": "..."}
        Called once at startup after loading history.
        """
        if self.client is None:
            raise RuntimeError("Client not initialized.")

        self._system_prompt = system_prompt

        # Convert history to Gemini format: "agent" → "model"
        gemini_history: list[types.Content] = []
        for msg in (history or []):
            role = "model" if msg["role"] == "agent" else "user"
            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg["text"])]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
        )
        self._chat = self.client.chats.create(
            model=MODEL,
            history=gemini_history,
            config=config,
        )
        log.info(f"Chat session created, loaded {len(gemini_history)} messages.")

    def send(self, message: str, system_prompt: str = "") -> str:
        """
        Sends a message within the current chat session.
        If no session exists — creates an empty one.
        """
        if self.client is None:
            raise RuntimeError("Client not initialized.")

        if self._chat is None:
            log.warning("Chat session not initialized, creating empty session.")
            self.start_chat(history=[], system_prompt=system_prompt)

        log.info(f"→ [{self.model}]: {message[:80]}{'...' if len(message) > 80 else ''}")
        response = self._chat.send_message(message)
        text = response.text or ""
        log.info(f"← Response: {text[:80]}{'...' if len(text) > 80 else ''}")
        return text
