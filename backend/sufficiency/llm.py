"""
LLM access layer for the Information Sufficiency Evaluator.

Real mode  – set env var LLM_API_KEY (+ optional LLM_BASE_URL, LLM_MODEL).
             Any OpenAI-compatible endpoint works (OpenAI, Groq, Ollama, …).
             HTTP requests use stdlib urllib only – no extra dependencies.

Mock mode  – no API key needed; a keyword-overlap heuristic lets the whole
             app run completely offline.  Results are DEMO ONLY and must NOT
             be reported as evaluation numbers.
"""

import json
import os
import random
import re
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Stopwords & text utilities
# ---------------------------------------------------------------------------
_STOP = frozenset(
    "a an the of in on at to for by is was were are who what which when "
    "where how did does do from with as and or that this it its be been "
    "has have had his her their about after before".split()
)


def terms(text: str) -> list[str]:
    """Return non-stop, 3+-char lowercase word tokens from *text*."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower())
            if w not in _STOP and len(w) > 2]


def stem(word: str) -> str:
    """Simple prefix-5 pseudo-stem."""
    return word[:5]


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------
def mode() -> str:
    """Return 'remote' if LLM_API_KEY is set, otherwise 'mock'."""
    return "remote" if os.getenv("LLM_API_KEY") else "mock"


# ---------------------------------------------------------------------------
# Prompt templates (one per task kind)
# ---------------------------------------------------------------------------
PROMPTS: dict[str, str] = {
    "autorater": (
        "Question: {q}\n"
        "Context: {ctx}\n\n"
        "Is the context sufficient to answer the question? "
        "Reply SUFFICIENT or INSUFFICIENT on the first line, then one sentence explaining why."
    ),
    "migres": (
        "Answer the question using ONLY the information in the context below. "
        "If you cannot answer, reply with the single word 'unanswerable' on the first line, "
        "then summarise what information is missing.\n\n"
        "Question: {q}\n"
        "Context: {ctx}"
    ),
    "identify": (
        "Question: {q}\n"
        "Context: {ctx}\n\n"
        "What specific information is missing from the context to answer the question? "
        "If nothing is missing, reply exactly: 'No information is missing.'"
    ),
    "verify": (
        "Context: {ctx}\n\n"
        "Claimed missing information: {claim}\n\n"
        "Is the claimed missing information actually present in the context "
        "(synonyms, paraphrases, and reasonable inference all count)? "
        "Reply YES or NO on the first line."
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ask(kind: str, q: str = "", ctx: str = "", claim: str = "", temp: float = 0.0) -> str:
    """
    Call the LLM (or mock) for the given task *kind*.

    Parameters
    ----------
    kind  : one of 'autorater' | 'migres' | 'identify' | 'verify'
    q     : question text
    ctx   : context passage(s)
    claim : consensus gap claim (only used by 'verify')
    temp  : sampling temperature (0 = greedy, 0.5 = diverse)

    Returns
    -------
    Raw text response from the model (or heuristic in mock mode).
    """
    prompt = PROMPTS[kind].format(q=q, ctx=ctx, claim=claim)
    if mode() == "remote":
        return _remote(prompt, temp)
    return _mock(kind, q, ctx, claim, temp)


# ---------------------------------------------------------------------------
# Remote (real LLM) path
# ---------------------------------------------------------------------------
def _remote(prompt: str, temp: float) -> str:
    """Send *prompt* to an OpenAI-compatible endpoint and return the reply."""
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    api_key = os.environ.get("LLM_API_KEY", "")

    endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"

    payload = json.dumps({
        "model": model,
        "temperature": temp,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        url=endpoint,
        data=payload,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.load(resp)
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"LLM API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM API connection error: {exc.reason}") from exc


# ---------------------------------------------------------------------------
# Mock (offline heuristic) path
# ---------------------------------------------------------------------------
def _missing_words(q: str, ctx: str) -> list[str]:
    """Return question terms whose stems are absent from the context."""
    ctx_stems = {stem(w) for w in terms(ctx)}
    seen: dict[str, bool] = {}
    result = []
    for w in terms(q):
        s = stem(w)
        if s not in seen:
            seen[s] = True
            if s not in ctx_stems:
                result.append(w)
    return result


def _mock(kind: str, q: str, ctx: str, claim: str, temp: float) -> str:
    """
    Offline heuristic responses – DEMO ONLY.

    autorater : SUFFICIENT / INSUFFICIENT based on missing question words.
    migres    : 'unanswerable' if question words are missing.
    identify  : lists missing words; at temp>0 simulates hallucinated gaps ~30 % of the time.
    verify    : YES only when all claim words are in the context.
    """
    miss = _missing_words(q, ctx)

    if kind == "autorater":
        if miss:
            return f"INSUFFICIENT. The context does not contain information about: {', '.join(miss)}."
        return "SUFFICIENT. All key aspects of the question are addressed in the context."

    if kind == "migres":
        if miss:
            return f"unanswerable. The context is missing: {', '.join(miss)}."
        return "Answer found in context."

    if kind == "identify":
        # Occasionally simulate a hallucinated gap (present word reported as missing)
        if temp > 0 and random.random() < 0.30:
            present = [w for w in terms(q) if stem(w) in {stem(x) for x in terms(ctx)}]
            if present:
                fake = random.choice(present)
                return f"The context does not clearly explain: {fake}."
        if not miss:
            return "No information is missing."
        k = random.randint(max(1, len(miss) - 1), len(miss))
        subset = random.sample(miss, k)
        return f"The context does not mention: {', '.join(subset)}."

    if kind == "verify":
        # Accept if every stem of the claim's payload is in the context
        payload = claim.split(":", 1)[-1] if ":" in claim else claim
        claim_words = terms(payload)
        ctx_stems = {stem(w) for w in terms(ctx)}
        if not claim_words:
            return "NO"
        return "YES" if all(stem(w) in ctx_stems for w in claim_words) else "NO"

    raise ValueError(f"Unknown kind: {kind!r}")
