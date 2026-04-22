"""
agent_loop.py — manual tool-calling loop for Gemini.

Key behaviours:
  - AFC disabled: we execute every tool call ourselves
  - Error anti-hallucination: errors are wrapped with a hard "DO NOT MAKE UP RESULT" marker
  - Retry nudge: if tool errored and model gives up too early, we push it to try again
  - Loop detector: same tool+args repeated N times → hard stop
  - Output truncation: large tool results are clipped before being sent back
"""

import unicodedata
from collections import deque

from google.genai import types

import data.config as config
from data.logger import get_logger

log = get_logger("agent")

_NARRATION_RULE = (
    "\n\n[TRANSPARENCY RULE] Before calling a tool — write 1-2 sentences in plain language: "
    "what you're about to do and why. After getting the result — briefly say what happened, "
    "whether it worked, or what went wrong and how you'll fix it. "
    "Never mention tool names directly — describe the action in plain words."
)

_ANTI_HALLUCINATION = (
    "⛔ TOOL RETURNED AN ERROR. DO NOT MAKE UP THE RESULT. "
    "Do not pretend the action succeeded. Report this error to the user word for word:\n"
)

_TOOL_FIRST_NUDGE = (
    "[SYSTEM] You answered with text but this request requires using a tool. "
    "Do NOT describe what you would do — actually DO it using the available tools right now. "
    "Use the tools immediately. No explanations before acting."
)

# Keywords that signal the user expects a tool call (file ops, shell, search, etc.)
_TOOL_ICONS = {
    "read_file":      "📖 Reading file",
    "write_file":     "✏️ Writing file",
    "append_file":    "📝 Appending to file",
    "patch_file":     "🔧 Patching file",
    "delete_file":    "🗑️ Deleting",
    "rename_file":    "🔄 Renaming",
    "move_file":      "📦 Moving file",
    "list_files":     "📁 Listing files",
    "create_dir":     "📁 Creating folder",
    "search_files":   "🔍 Searching files",
    "run_shell":      "💻 Running command",
    "run_file":       "▶️ Running script",
    "list_processes": "⚙️ Checking processes",
    "kill_process":   "🛑 Stopping process",
}

_TOOL_KEYWORDS = [
    # корни — покрывают все формы слова
    "созда",      # создай, создать, создал, создание
    "запис",      # запиши, записать, запись, запишу
    "запомн",     # запомни, запомнить, запомнил
    "сохран",     # сохрани, сохранить, сохранение
    "удал",       # удали, удалить, удаление
    "прочита",    # прочитай, прочитать
    "чита",       # читай, читать
    "найд",       # найди, найдёт
    "наход",      # находи, находить
    "поиск",      # поиск, поискать
    "поищ",       # поищи
    "выполн",     # выполни, выполнить
    "запуст",     # запусти, запустить
    "добав",      # добавь, добавить, добавление
    "переимен",   # переименуй, переименовать
    "перемест",   # перемести, переместить
    "обнов",      # обнови, обновить, обновление
    "измен",      # измени, изменить, изменение
    "редакт",     # редактируй, редактировать
    "отмет",      # отметь, отметить
    "открой",     # открой, открыть
    "открыт",     # открытие, открытый
    # контекстные существительные — тоже покрывают все падежи
    "дневник",    # дневник, дневника, в дневнике
    "памят",      # память, памяти
    "интернет",   # интернет, интернета, в интернете, интернету
    "инет",       # инет, в инете
    "сети",       # в сети, из сети
    "сеть",       # сеть
    "файл",       # файл, файла, файлы, файлов
    "папк",       # папка, папку, папки
    "директор",   # директория, директории
    "скрипт",     # скрипт, скрипта, скрипты
    # английские
    "create", "write", "save", "delete", "remove", "read",
    "find", "search", "run", "append", "rename", "move",
    "update", "note", "diary", "file", "folder",
    "internet", "web", "online",
]

# Корни прошедшего времени — "записал" = записал/записала/записали/записало
# НЕ совпадает с "записать" (там "т", а не "л")
_FALSE_CLAIM_KEYWORDS = [
    "записал",       # записал/а/и
    "сохранил",      # сохранил/а/и
    "создал",        # создал/а/и
    "добавил",       # добавил/а/и
    "обновил",       # обновил/а/и
    "удалил",        # удалил/а/и
    "написал",       # написал/а/и
    "отметил",       # отметил/а/и
    "запомнил",      # запомнил/а/и
    "выполнил",      # выполнил/а/и
    "нашёл", "нашла",
    "прочитал",      # прочитал/а
    "переименовал",  # переименовал/а
    "переместил",    # переместил/а
    "изменил",       # изменил/а
    "открыл",        # открыл/а
    # английские
    "i've written", "i've saved", "i've created", "i've added",
    "i've updated", "i've deleted", "i've noted", "i have written",
    "i've found", "i've read",
]


def _looks_like_tool_request(message: str) -> bool:
    low = message.lower()
    return any(kw in low for kw in _TOOL_KEYWORDS)


def _looks_like_false_claim(text: str) -> bool:
    """Model claims to have done something without calling a tool."""
    low = text.lower()
    return any(kw in low for kw in _FALSE_CLAIM_KEYWORDS)


# ── Internet search helpers ───────────────────────────────────────────────────

def _build_tools_config(client, tools: list, internet_mode: str):
    """
    Returns (tools_list, tool_config) for GenerateContentConfig.
    When internet is enabled, google_search and custom functions
    must be in separate types.Tool objects — putting them together breaks search.
    """
    use_search = internet_mode != "never"

    declarations = [
        types.FunctionDeclaration.from_callable(
            client=client._api_client,
            callable=fn,
        )
        for fn in tools
    ]

    tools_list = []
    if use_search:
        tools_list.append(types.Tool(google_search=types.GoogleSearch()))
    if declarations:
        tools_list.append(types.Tool(function_declarations=declarations))

    tool_config = (
        types.ToolConfig(include_server_side_tool_invocations=True)
        if use_search else None
    )
    return tools_list, tool_config


def _extract_sources(candidate) -> str:
    """Format grounding sources from a response candidate into a markdown list."""
    gm = getattr(candidate, "grounding_metadata", None)
    if not gm:
        return ""
    chunks = getattr(gm, "grounding_chunks", None) or []
    sources = []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if web and getattr(web, "title", None) and getattr(web, "uri", None):
            sources.append(f"- [{web.title}]({web.uri})")
    if not sources:
        return ""
    return "\n\n**Sources:**\n" + "\n".join(sources[:5])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_spam(text: str) -> bool:
    """Return True if text looks like emoji spam or repeating phrase loop (for interim narration)."""
    if len(text) <= 200:
        return False
    sample = text[-200:]
    letter_count = sum(
        1 for c in sample
        if unicodedata.category(c).startswith(("L", "N", "Z"))
    )
    if letter_count / len(sample) < 0.3:
        return True
    if len(text) > 150:
        tail = text[-300:]
        for phrase_len in range(10, 61):
            phrase = tail[-phrase_len:]
            if tail.count(phrase) >= 4:
                log.warning(f"Spam phrase detected in interim: '{phrase[:30]}' x{tail.count(phrase)}")
                return True
    return False


def _is_meaningful(text: str) -> bool:
    """Return False if text looks like an emoji/symbol loop or a repeating phrase loop."""
    if not text or len(text) < 20:
        return False

    # Check for low letter/number density (emoji spam)
    if len(text) > 200:
        sample = text[-200:]
        letter_count = sum(
            1 for c in sample
            if unicodedata.category(c).startswith(("L", "N", "Z"))
        )
        if letter_count / len(sample) < 0.3:
            return False

    # Check for repeating phrase loop (e.g. "наступило? наступило? наступило?")
    # Take the last 300 chars, split into chunks and check for repetition
    if len(text) > 150:
        tail = text[-300:]
        # Try phrase lengths from 10 to 60 chars
        for phrase_len in range(10, 61):
            phrase = tail[-phrase_len:]
            # Count non-overlapping occurrences in the tail
            count = tail.count(phrase)
            if count >= 4:  # same phrase appears 4+ times in last 300 chars → loop
                log.warning(f"Repetition loop detected: phrase '{phrase[:30]}' x{count}")
                return False

    return True


def _is_error(result: dict) -> bool:
    return str(result.get("status", "")).lower() == "error" or "error" in result


def _truncate(result: dict, tool_name: str, limit: int) -> dict:
    out = {}
    for k, v in result.items():
        s = str(v)
        if len(s) > limit:
            log.warning(f"Truncating {tool_name}.{k}: {len(s)} → {limit} chars")
            out[k] = s[:limit] + "\n...[truncated — output too large]"
        else:
            out[k] = v
    return out


def _wrap_error(result: dict) -> dict:
    error_text = result.get("error", str(result))
    return {"status": "error", "error": _ANTI_HALLUCINATION + error_text}


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(client, model: str, system_prompt: str,
        history: list[dict], message: str, tools: list,
        on_interim=None) -> str:
    """
    Runs the manual tool-calling loop and returns the final text response.

    client        — genai.Client instance
    model         — model name string
    system_prompt — agent system instruction
    history       — list of {"role": "user"|"agent", "text": "..."}, NOT including current message
    message       — current user message (with time prefix already injected)
    tools         — list of Python functions; SDK auto-generates schema from docstrings
    """
    max_rounds      = config.get_max_tool_rounds()
    max_contin      = config.get_max_continuations()
    max_nudges      = config.get_max_tool_nudges()
    loop_threshold  = config.get_loop_detect_threshold()
    trunc_limit     = config.get_max_result_chars()
    max_out_tokens  = config.get("max_output_tokens") or 4096

    # Convert history to Gemini format, dropping consecutive same-role messages
    gemini_history: list[types.Content] = []
    for msg in history:
        role = "model" if msg["role"] == "agent" else "user"
        text = (msg.get("text") or "").strip() or ("(empty)" if role == "model" else " ")
        if gemini_history and gemini_history[-1].role == role:
            gemini_history[-1] = types.Content(role=role, parts=[types.Part(text=text)])
        else:
            gemini_history.append(types.Content(role=role, parts=[types.Part(text=text)]))

    # Gemini requires history to start with "user" — drop leading model messages
    # (can happen when history is trimmed at the 100-message boundary)
    while gemini_history and gemini_history[0].role != "user":
        gemini_history.pop(0)
        log.warning("Dropped leading model message from history (Gemini requires user-first)")

    tools_map: dict = {fn.__name__: fn for fn in tools}
    internet_mode = config.get_internet_mode()
    tools_list, tool_config = _build_tools_config(client, tools, internet_mode)
    log.info(f"Internet mode: {internet_mode}, tools: {[type(t).__name__ for t in tools_list]}")

    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            system_instruction=(system_prompt or "") + _NARRATION_RULE,
            tools=tools_list,
            tool_config=tool_config,
            temperature=config.get_temperature(),
            max_output_tokens=max_out_tokens,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
        history=gemini_history,
    )

    current_message = message
    recent_sigs: deque = deque(maxlen=loop_threshold * 3)
    collected_text: list[str] = []
    last_chunk_tail: str = ""   # used to detect continuation loops
    had_errors       = False
    had_success      = False
    retry_nudges     = 0
    contin_nudges    = 0
    tool_first_nudges = 0
    original_message  = message

    log.info(f"Agent loop start — model={model}, max_rounds={max_rounds}")

    for round_idx in range(max_rounds):
        response = chat.send_message(current_message)

        candidate = (response.candidates or [None])[0]
        if not candidate:
            log.error("Empty candidates — safety filter?")
            break

        finish_reason = str(getattr(candidate, "finish_reason", "") or "")
        parts = (candidate.content.parts if candidate.content else None) or []

        tool_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        # Detect server-side google_search usage
        has_search = any(
            getattr(getattr(p, "executable_code", None), "language", None) == "GEMINI_SEARCH"
            or getattr(p, "search_queries", None)
            for p in parts
        ) or bool(getattr(getattr(candidate, "grounding_metadata", None), "grounding_chunks", None))
        if has_search:
            had_success = True  # internet search counts as a successful tool use — don't nudge
            if on_interim:
                on_interim("[tool]🌐 Searching the web")

        # ── Text-only response: model is done (or giving up) ─────────────────
        if not tool_calls:
            text_chunks = [p.text for p in parts if getattr(p, "text", None)]
            round_text  = "".join(text_chunks).strip()

            # No tools called yet but request needs one — nudge up to N times
            # Fires if: original message looks like a tool request OR model claims to have done something without calling a tool
            needs_nudge = (
                _looks_like_tool_request(original_message)
                or (round_text and _looks_like_false_claim(round_text))
            )
            if (not had_success
                    and tool_first_nudges < max_nudges
                    and needs_nudge
                    and round_idx < max_rounds - 1):
                tool_first_nudges += 1
                log.info(f"Tool-first nudge #{tool_first_nudges} — model skipped tools (false_claim={bool(round_text and _looks_like_false_claim(round_text))})")
                if round_text and on_interim:
                    on_interim(round_text)   # show immediately, not at end
                current_message = _TOOL_FIRST_NUDGE
                continue

            # Model gave up after an error — nudge it to try again
            elif (had_errors and not had_success
                    and retry_nudges < 2
                    and round_idx < max_rounds - 1):
                retry_nudges += 1
                log.info(f"Retry nudge #{retry_nudges} — model gave up after error")
                if round_text and on_interim:
                    on_interim(round_text)   # show immediately, not at end
                current_message = (
                    "[SYSTEM] You stopped after a tool error without completing the task. "
                    "Don't give up. Analyse what went wrong, adjust the parameters, "
                    "and try a different approach. Use the tools again."
                )
                continue

            # Response was cut off by token limit — but only if text looks meaningful
            elif ("MAX_TOKENS" in finish_reason.upper()
                    and contin_nudges < max_contin
                    and round_idx < max_rounds - 1
                    and _is_meaningful(round_text)):
                # Extra guard: if new chunk starts with the tail of the previous chunk
                # it means the model is looping instead of continuing → hard stop
                if last_chunk_tail and round_text.startswith(last_chunk_tail[:60]):
                    log.warning(
                        f"Continuation loop detected: new chunk repeats previous tail. Stopping."
                    )
                    collected_text.append(round_text)
                    break
                contin_nudges += 1
                log.info(f"MAX_TOKENS — continuation #{contin_nudges}")
                last_chunk_tail = round_text[-80:].strip()  # remember tail for next check
                if round_text and on_interim:
                    on_interim(round_text)   # show immediately, not at end
                current_message = (
                    "[SYSTEM CONTINUE] Continue exactly from where you left off. "
                    "Do not repeat already written text."
                )
                continue

            # Final round — collect text for the return value
            if round_text:
                if not _is_meaningful(round_text) and len(round_text) > 200:
                    log.warning(f"Round text looks like emoji loop ({len(round_text)} chars) — discarding")
                    round_text = "[Ответ был обрезан: модель ушла в цикл повторений. Попробуй переформулировать запрос.]"
                collected_text.append(round_text)
            log.info(f"Agent loop finished in {round_idx + 1} round(s)")
            break

        # ── Has tool calls ────────────────────────────────────────────────────
        # Model may have written text alongside the tool calls ("thinking aloud").
        # Emit as interim — don't add to the final answer.
        for p in parts:
            if getattr(p, "text", None) and p.text.strip():
                interim_text = p.text.strip()
                if _is_spam(interim_text):
                    log.warning(f"Spam in tool narration suppressed ({len(interim_text)} chars)")
                elif on_interim:
                    on_interim(interim_text)

        response_parts: list = []

        for fc in tool_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}

            # Notify via interim so the user can see tool activity in real time
            if on_interim:
                label = _TOOL_ICONS.get(name, f"🔧 {name}")
                first_arg = next(iter(args.values()), "") if args else ""
                hint = f": {str(first_arg)[:50]}" if first_arg else ""
                on_interim(f"[tool]{label}{hint}")

            # Loop detector
            sig = f"{name}:{sorted(args.items())}"
            recent_sigs.append(sig)
            if recent_sigs.count(sig) >= loop_threshold:
                log.error(f"Loop detected: '{name}' called {loop_threshold}+ times with same args")
                collected_text.append(
                    f"I detected a loop: the same tool call was repeated {loop_threshold} times "
                    f"with identical parameters. Stopping automatically. "
                    f"Please rephrase or clarify your request."
                )
                return "\n\n".join(collected_text)

            # Execute tool
            func = tools_map.get(name)
            log.info(f"[TOOL CALL] {name}({args})")
            if func:
                try:
                    result = func(**args)
                except Exception as e:
                    result = {"status": "error", "error": f"{name} raised an exception: {e}"}
            else:
                result = {"status": "error", "error": f"Tool '{name}' is not registered"}

            if not isinstance(result, dict):
                result = {"status": "ok", "result": str(result)}

            if _is_error(result):
                had_errors = True
                log.warning(f"[TOOL ERROR] {name}: {result.get('error', result)}")
                result = _wrap_error(result)
            else:
                had_success = True
                log.info(f"[TOOL OK] {name}: {str(result)[:120]}")

            result = _truncate(result, name, trunc_limit)
            response_parts.append(
                types.Part.from_function_response(name=name, response=result)
            )

        current_message = response_parts

    else:
        log.warning("Agent loop reached max rounds without finishing")

    if not collected_text:
        return "Task completed, but the model returned no text. Please try again."

    result_text = "\n\n".join(collected_text)

    # Append web sources if grounding was used in the last response
    try:
        last_candidate = (response.candidates or [None])[0]  # type: ignore[possibly-undefined]
        sources = _extract_sources(last_candidate)
        if sources:
            log.info("Grounding sources appended to response.")
            result_text += sources
    except Exception:
        pass

    return result_text
