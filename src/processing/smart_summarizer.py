"""
Two-stage smart summarization: rule-based pre-filter (Stage 1) and optional OpenAI notes (Stage 2).
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Iterable, Pattern

from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = """You are an expert technical note-taker for online courses.
You receive raw auto-generated subtitle text from a training video (already lightly cleaned).
Your job is to convert it into structured, concise study notes in Markdown format.

Reference label from the platform (may be a real video title or may be an auto filename like
auto_generated_captions_3 — ignore it for the main heading if it looks machine-made): {video_title}

Return ONLY valid Markdown. Structure it exactly like this:

## <Short descriptive title you invent from the transcript>

The FIRST line of your output MUST be exactly one Markdown level-2 heading (## ...).
That title MUST summarize the main topic in plain language (about 3–12 words) using ONLY
information from the transcript. Do NOT use upload filenames, auto_generated_*, captions,
WEBVTT, or similar tokens in this heading. If the reference label above is clearly a
human-readable course or lecture title (not a filename), you may use it; otherwise invent
a better title from the content.

### Overview
2-3 sentence summary of what this video covers.

### Key Concepts
- **ConceptName**: clear explanation
- **ConceptName**: clear explanation
(include all important technical terms, tools, frameworks mentioned)

### Detailed Notes
Flowing paragraphs of the actual teaching content. Preserve technical accuracy.
Remove all conversational filler, student Q&A noise, and repeated explanations.
Keep instructor explanations that add real value.

### Definitions
| Term | Definition |
|------|------------|
(only if 3+ technical terms appear, otherwise omit this section)

### Key Takeaways
- bullet point summary of the most important things to remember
"""


def _looks_like_auto_upload_label(name: str) -> bool:
    """Return True if ``name`` looks like an auto-generated asset/filename, not a human title."""
    n = (name or "").strip().lower()
    if not n:
        return True
    if re.search(r"auto[_\s-]*generated", n):
        return True
    if re.search(r"captions?_\d+", n) or re.search(r"_captions?_\d+", n):
        return True
    if re.search(r"\bwebvtt\b", n):
        return True
    if re.fullmatch(r"[\w-]+_\d+", n.replace(" ", "_")):
        return True
    return False


def _title_from_filtered_body(body: str, max_words: int = 12) -> str:
    """Build a short heading from pre-filtered subtitle prose when no good label exists."""
    plain = re.sub(r"\s+", " ", (body or "").strip())
    if not plain:
        return "Video Notes"
    words = plain.split()
    if len(words) <= max_words:
        return plain
    return " ".join(words[:max_words])


def _env_ai_summarizer_enabled() -> bool:
    """Return True unless USE_AI_SUMMARIZER is set to a false-like value."""
    val = os.getenv("USE_AI_SUMMARIZER", "true").strip().lower()
    return val not in ("0", "false", "no", "off")


def _split_into_sentences(text: str) -> list[str]:
    """Split text into rough sentences (newlines and . ! ? boundaries)."""
    if not text.strip():
        return []
    sentences: list[str] = []
    for block in re.split(r"\n+", text.strip()):
        block = block.strip()
        if not block:
            continue
        parts = re.split(r"(?<=[.!?])\s+", block)
        for p in parts:
            p = p.strip()
            if p:
                sentences.append(p)
    return sentences


def _word_count(s: str) -> int:
    """Count whitespace-separated tokens in a string."""
    return len(re.findall(r"\S+", s))


def _has_technical_hint(sentence: str) -> bool:
    """
    Heuristic: short sentences that might still be technical are kept.
    """
    if re.search(r"\d", sentence):
        return True
    if re.search(r"[A-Z]{2,}", sentence):
        return True
    if re.search(r"[/\\]", sentence):
        return True
    if re.search(r"\b\w+-\w+", sentence):
        return True
    if re.search(r"[`@#$%^&*()_+=\[\]{}|]", sentence):
        return True
    words = re.findall(r"\b\w+\b", sentence)
    if any(len(w) >= 10 for w in words):
        return True
    return False


def _sentence_matches_any(sentence_lower: str, patterns: Iterable[Pattern[str]]) -> bool:
    """Return True if any pattern matches anywhere in the sentence."""
    for pat in patterns:
        if pat.search(sentence_lower):
            return True
    return False


# Standalone greeting/sign-off lines (full string, lowercase)
_GREETING_SIGNOFF_STANDALONE: list[Pattern[str]] = [
    re.compile(
        r"^(good\s+(morning|afternoon|evening|night)|hello|hi(\s+there)?|hey\s+(everyone|class|all)|"
        r"bye|goodbye|see you(\s+later|tomorrow)?|talk to you later|thank you|thanks(\s+so\s+much)?|"
        r"thank you everyone|appreciate it|welcome back|how are you|have a (good|great|nice) (day|weekend))"
        r"[\s.!?]*$",
        re.IGNORECASE,
    ),
]

# Phrases that remove the whole sentence only when short (avoid "welcome to Kubernetes")
_GREETING_SIGNOFF_SHORT: list[Pattern[str]] = [
    re.compile(r"\b(good\s+(morning|afternoon|evening|night))\b"),
    re.compile(r"^(hello|hi there|hey everyone|hey class)[\s.!?]*$"),
    re.compile(r"\b(bye|goodbye|see you soon|talk to you later)\b"),
    re.compile(r"^(thank you|thanks)(\s+everyone|\s+so\s+much)?[\s.!?]*$"),
    re.compile(r"^welcome back[\s.!?]*$"),
    re.compile(r"\bhow\s+are\s+you\b"),
    re.compile(r"\bhave a (good|great|nice) (day|weekend)\b"),
]

_ACK_STANDALONE_PATTERNS: list[Pattern[str]] = [
    re.compile(r"^(okay|ok|k|yes|no|yeah|yep|nope|alright|all right|right|sure|hmm|hm|uh|um|uh-?huh|mhm|mm-?hm)[\s.!?]*$"),
    re.compile(r"^(okay|ok|yes|no|yeah|alright)[\s,]+(okay|ok|yes|no|yeah|alright)[\s.!?]*$"),
]

_META_CLASS_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\bclass\s+is\s+(started|starting)\b"),
    re.compile(r"\bwe('ll|\s+will)\s+stop\s+here\b"),
    re.compile(r"\bsee you\s+(tomorrow|next week|on monday)\b"),
    re.compile(r"\bone\s+minute\b"),
    re.compile(r"\btake a (short\s+)?break\b"),
    re.compile(r"\bany\s+questions\s+(before we|so far)\b"),
    re.compile(r"\blet's\s+(get\s+started|begin)\b"),
    re.compile(r"\bwe are (now )?recording\b"),
]

_ADMIN_LOGISTICS_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\battendance\s+(sheet|form)?\b"),
    re.compile(r"\bslack\s+(channel|workspace)\b"),
    re.compile(r"\blms\b"),
    re.compile(r"\bsupport\s+team\b"),
    re.compile(r"\bbing\s+them\b"),
    re.compile(r"\boffice\s+hours\b"),
    re.compile(r"\bcourse\s+materials\b"),
    re.compile(r"\bdeadline\s+for\b"),
    re.compile(r"\bsubmit\s+(on|via|through)\b"),
]

_SORRY_REPEAT_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\b(sorry|excuse me|pardon me)\b"),
    re.compile(r"\bcan you\s+(repeat|say that again)\b"),
    re.compile(r"\bcould you\s+repeat\b"),
    re.compile(r"\bwhat did you say\b"),
    re.compile(r"\bi didn'?t (catch|hear)\b"),
]


def _is_mostly_noise_sentence(sentence: str) -> bool:
    """Return True if sentence should be dropped as noise."""
    s = sentence.strip()
    if not s:
        return True
    sl = s.lower()
    wc = _word_count(s)

    for pat in _GREETING_SIGNOFF_STANDALONE:
        if pat.match(s.strip()):
            return True
    if wc <= 12 and _sentence_matches_any(sl, _GREETING_SIGNOFF_SHORT):
        return True
    if _sentence_matches_any(sl, _ACK_STANDALONE_PATTERNS):
        return True
    if wc <= 18 and _sentence_matches_any(sl, _META_CLASS_PATTERNS):
        return True
    if wc <= 18 and _sentence_matches_any(sl, _ADMIN_LOGISTICS_PATTERNS):
        return True
    if wc <= 16 and _sentence_matches_any(sl, _SORRY_REPEAT_PATTERNS):
        return True

    if wc < 6 and not _has_technical_hint(s):
        return True

    return False


def _similarity(a: str, b: str) -> float:
    """Return normalized similarity ratio in ``[0, 1]`` for near-duplicate detection."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _dedupe_consecutive_similar(sentences: list[str], threshold: float = 0.82) -> list[str]:
    """Keep first of consecutive pairs with similarity strictly above threshold."""
    if not sentences:
        return []
    out: list[str] = [sentences[0]]
    for i in range(1, len(sentences)):
        if _similarity(sentences[i], out[-1]) > threshold:
            continue
        out.append(sentences[i])
    return out


def _sentences_to_paragraphs(sentences: list[str]) -> str:
    """Join sentences into readable paragraphs (roughly 4–6 sentences per paragraph)."""
    if not sentences:
        return ""
    paras: list[str] = []
    buf: list[str] = []
    for s in sentences:
        buf.append(s.rstrip())
        if len(buf) >= 5:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return "\n\n".join(paras)


def rule_based_filter(text: str) -> str:
    """
    Run only Stage 1: strip conversational noise and near-duplicate consecutive lines.

    Args:
        text: Cleaned subtitle text (e.g. after clean_subtitle_text).

    Returns:
        Filtered text as paragraphs.
    """
    if not text or not text.strip():
        return ""
    sentences = _split_into_sentences(text)
    kept = [s for s in sentences if not _is_mostly_noise_sentence(s)]
    kept = _dedupe_consecutive_similar(kept, threshold=0.82)
    return _sentences_to_paragraphs(kept)


def _fallback_markdown(video_title: str, body: str) -> str:
    """Wrap body under a single level-2 heading when AI is unavailable."""
    vt = (video_title or "").strip()
    if vt and not _looks_like_auto_upload_label(vt):
        title = vt
    else:
        title = _title_from_filtered_body(body)
    body_stripped = body.strip()
    if not body_stripped:
        body_stripped = "_No substantive content after filtering._"
    return f"## {title}\n\n{body_stripped}\n"


def _openai_summarize(
    prefiltered_text: str,
    video_title: str,
    api_key: str,
) -> str:
    """
    Call OpenAI chat completion; try gpt-4o then gpt-3.5-turbo.

    Returns:
        Model markdown output or raises on total failure.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    user_content = prefiltered_text
    system_prompt = _SYSTEM_PROMPT.replace("{video_title}", video_title)

    last_error: Exception | None = None
    for model in ("gpt-4o", "gpt-3.5-turbo"):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )
            choice = resp.choices[0].message.content
            if choice and choice.strip():
                return choice.strip()
        except Exception as e:
            last_error = e
            continue
    if last_error:
        raise last_error
    raise RuntimeError("OpenAI returned empty content")


def smart_summarize(
    raw_text: str,
    video_title: str = "Video Notes",
    use_ai: bool = True,
    openai_api_key: str | None = None,
) -> str:
    """
    Returns structured Markdown string.

    Stage 1 always runs. Stage 2 (OpenAI) runs only if use_ai is True, the global
    USE_AI_SUMMARIZER env flag is enabled, pre-filtered text is non-empty, and an
    API key is available.

    Args:
        raw_text: Text after clean_subtitle_text (or equivalent).
        video_title: Optional reference label (e.g. Vimeo title or upload stem); used in the
            system prompt only. The model must not copy machine-made filenames into ``##``.
        use_ai: If False, only rule-based filtering is applied (wrapped in basic markdown).
        openai_api_key: Optional key; defaults to OPENAI_API_KEY from the environment.

    Returns:
        Markdown suitable for PDF generation.
    """
    filtered = rule_based_filter(raw_text)

    env_allows_ai = _env_ai_summarizer_enabled()
    key = (openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()

    should_call_ai = (
        bool(use_ai)
        and env_allows_ai
        and bool(filtered.strip())
        and bool(key)
    )

    if not should_call_ai:
        return _fallback_markdown(video_title, filtered)

    try:
        return _openai_summarize(filtered, video_title, key)
    except Exception:
        return _fallback_markdown(video_title, filtered)
