"""Context compression for DA-Agent history messages.

Compresses old observation and code-block content in history_messages
to reduce cumulative input tokens sent to the LLM. Only modifies the
message *copy* used for prediction — the original history and saved
trajectory are never touched.

Two strategies:
  1. Observation summarization — replace verbose SQL / bash output
     from old steps with a compact rule-based summary.
  2. Code-block stripping — replace CreateFile / EditFile code bodies
     from old steps with a short stub (the file is already on disk).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, NamedTuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompressionConfig:
    """Immutable config controlling context compression behaviour."""

    enabled: bool = False
    """Master switch — ``False`` by default; ``--compress_context`` turns on."""

    recent_full_window: int = 5
    """Number of most-recent step pairs kept fully intact."""

    obs_compress_threshold: int = 200
    """Only compress observations longer than this (chars)."""

    obs_summary_max_chars: int = 150
    """Max chars for a compressed observation summary."""

    strip_code_blocks: bool = True
    """Whether to strip CreateFile / EditFile code blocks from old steps."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compress_history_messages(
    messages: List[Dict],
    config: CompressionConfig,
) -> List[Dict]:
    """Return a *new* message list with old steps compressed.

    Layout assumption::

        messages = [system, user_0, asst_0, user_1, asst_1, ...]

    Each step = 1 user message (observation) + 1 assistant message
    (thought + action).  The system message at index 0 is never touched.
    """
    if not config.enabled or len(messages) <= 1:
        return list(messages)

    system_msg = messages[0]

    # Collect step pairs --------------------------------------------------
    # After the system message, messages *should* alternate user / assistant.
    # However trailing messages (e.g. repetition warnings) may break the
    # pattern — collect pairs greedily and keep any remainder.
    body = messages[1:]
    pairs: List[_StepPair] = []
    i = 0
    while i + 1 < len(body):
        pairs.append(_StepPair(user=body[i], assistant=body[i + 1]))
        i += 2
    trailing = body[i:]  # 0 or 1 leftover message

    # Determine compression boundary -------------------------------------
    compress_up_to = max(0, len(pairs) - config.recent_full_window)

    result: List[Dict] = [system_msg]
    for idx, pair in enumerate(pairs):
        if idx < compress_up_to:
            result.append(_compress_observation(pair.user, config))
            result.append(_compress_action(pair.assistant, config))
        else:
            result.append(pair.user)
            result.append(pair.assistant)

    result.extend(trailing)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _StepPair(NamedTuple):
    user: Dict
    assistant: Dict


_OBS_PREFIX = "Observation: "


def _compress_observation(msg: Dict, config: CompressionConfig) -> Dict:
    """Compress a user observation message.  Returns a *new* dict."""
    text = _extract_text(msg)
    if not text.startswith(_OBS_PREFIX):
        return msg  # not a standard observation — pass through

    body = text[len(_OBS_PREFIX):]

    if len(body) <= config.obs_compress_threshold:
        return msg  # short enough already

    summary = _summarize_observation(body, config.obs_summary_max_chars)
    compressed_text = f"{_OBS_PREFIX}[compressed] {summary}"
    return _with_text(msg, compressed_text)


def _compress_action(msg: Dict, config: CompressionConfig) -> Dict:
    """Compress an assistant action message.  Returns a *new* dict."""
    if not config.strip_code_blocks:
        return msg

    text = _extract_text(msg)
    new_text = _strip_code_blocks(text)
    if new_text is text:  # identity check — nothing changed
        return msg
    return _with_text(msg, new_text)


# ---------------------------------------------------------------------------
# Observation summarization (rule-based, no LLM call)
# ---------------------------------------------------------------------------

# Patterns indicating the observation is an error / traceback.
_ERROR_INDICATORS = (
    "error", "traceback", "exception", "failed",
    "errno", "syntaxerror", "typeerror", "valueerror",
    "filenotfounderror", "keyerror", "indexerror",
    "modulenotfounderror", "importerror", "attributeerror",
)

# Patterns indicating a file operation confirmation (already short).
_FILE_CONFIRM_INDICATORS = (
    "created and written successfully",
    "edited and saved successfully",
    "saved successfully",
    "File created",
)


def _summarize_observation(body: str, max_chars: int) -> str:
    """Rule-based observation summarization."""
    body_lower = body.lower()
    lines = body.strip().split("\n")

    # 1. File-operation confirmations — keep as-is (should be short).
    for phrase in _FILE_CONFIRM_INDICATORS:
        if phrase.lower() in body_lower:
            return body[:max_chars]

    # 2. Error / traceback — give 2× budget so debug info survives.
    for phrase in _ERROR_INDICATORS:
        if phrase in body_lower:
            return body[: max_chars * 2]

    # 3. Pandas DataFrame repr  (e.g.  "[4 rows x 7 columns]")
    shape_match = re.search(
        r"\[(\d+)\s+rows?\s*[x×]\s*(\d+)\s+columns?\]", body
    )
    if shape_match:
        header = lines[0][:80] if lines else ""
        return (
            f"DataFrame: {header}... "
            f"({shape_match.group(1)} rows x {shape_match.group(2)} cols)"
        )

    # 4. Tabular data (header + data rows with consistent separators).
    if len(lines) > 2:
        first = lines[0]
        if "," in first or "\t" in first or "  " in first:
            header = first[:80]
            n_data = len(lines) - 1
            return f"Table: {header}... ({n_data} rows)"

    # 5. Generic — first meaningful line + total size.
    first_line = next((ln for ln in lines if ln.strip()), body)[:80]
    return f"{first_line}... ({len(body)} chars total)"


# ---------------------------------------------------------------------------
# Code-block stripping for CreateFile / EditFile actions
# ---------------------------------------------------------------------------

# Regex patterns matching the three __repr__ formats from action.py.
#
#   Format A  (CreateFile line 198):
#       CreateFile(filepath="xxx.py"):\n```\n{code}\n```
#
#   Format B  (CreateFile alternate, line 448):
#       CreateFile(filepath='xxx.py':\n'''\n{code}\n''')
#
#   Format C  (EditFile line 459):
#       EditFile(filepath="xxx.py"):\n```\n{code}\n```

_CODE_BLOCK_PATTERNS = [
    # Format A & C  —  backtick code blocks
    re.compile(
        r"((?:CreateFile|EditFile)\(filepath=[\"'][^\"']+[\"']\)):\s*\n```\n"
        r"(.*?)"
        r"\n```",
        re.DOTALL,
    ),
    # Format B  —  triple-quote code blocks
    #   Actual __repr__: CreateFile(filepath='xxx.py':\n'''\n{code}\n''')
    #   Note: the colon is inside the parens, closing ) is after '''
    re.compile(
        r"(CreateFile\(filepath='[^']+')"
        r":\s*\n'''\n"
        r"(.*?)"
        r"\n'''\)",
        re.DOTALL,
    ),
]

_STUB_TEMPLATE = "[history: {action_type} '{filename}' — {lines} {word} already written to disk]"

# Regex to extract action type and filepath from a captured header group.
_HEADER_RE = re.compile(r"(CreateFile|EditFile)\(filepath=[\"']([^\"']+)[\"']")


def _code_block_replacer(m: re.Match) -> str:
    """Replacement function for code-block regex matches.

    Returns a note that does NOT start with ``ActionName(`` so the agent
    cannot mistake it for a new action to reproduce.
    """
    header = m.group(1)
    code_body = m.group(2)
    n_lines = code_body.count("\n") + 1 if code_body else 0
    word = "line" if n_lines == 1 else "lines"

    hm = _HEADER_RE.search(header)
    if hm:
        action_type = hm.group(1)
        filename = hm.group(2).rsplit("/", 1)[-1]  # basename only
    else:
        action_type = "file operation"
        filename = "?"

    return _STUB_TEMPLATE.format(
        action_type=action_type, filename=filename, lines=n_lines, word=word
    )


def _strip_code_blocks(text: str) -> str:
    """Strip CreateFile / EditFile code bodies from action text.

    Returns the *original object* (same identity) if nothing changed,
    so callers can do a cheap ``is`` check.
    """
    result = text
    for pattern in _CODE_BLOCK_PATTERNS:
        result = pattern.sub(_code_block_replacer, result)

    # Return the original object if nothing changed (identity optimisation).
    if result == text:
        return text
    return result


# ---------------------------------------------------------------------------
# Message dict helpers (preserve structure, create new dicts)
# ---------------------------------------------------------------------------

def _extract_text(msg: Dict) -> str:
    """Get the text payload from a standard message dict."""
    content = msg.get("content", [])
    if isinstance(content, list) and content:
        return content[0].get("text", "")
    if isinstance(content, str):
        return content
    return ""


def _with_text(msg: Dict, new_text: str) -> Dict:
    """Return a *new* message dict with ``text`` replaced."""
    content = msg.get("content", [])
    if isinstance(content, list):
        new_content = [{"type": "text", "text": new_text}]
        if len(content) > 1:
            new_content.extend(content[1:])
        return dict(msg, content=new_content)
    return dict(msg, content=new_text)
