import math, re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from . import llm

N_SAMPLES, TEMP, THRESHOLD = 5, 0.5, 0.3
METHODS = ["autorater", "migres", "identify_only", "identify_verify"]

_st = None
def _embed(texts):
    global _st
    if _st is not False:
        try:
            if _st is None:
                from sentence_transformers import SentenceTransformer
                _st = SentenceTransformer("all-MiniLM-L6-v2")
            return [list(v) for v in _st.encode(texts, normalize_embeddings=True)]
        except Exception:  # fallback: bag-of-words vectors
            _st = False
    vocab = sorted({w for t in texts for w in llm.terms(t)})
    vecs = []
    for t in texts:
        c = Counter(llm.terms(t)); n = math.sqrt(sum(v * v for v in c.values())) or 1
        vecs.append([c[w] / n for w in vocab])
    return vecs

def consensus(hyps, thr=THRESHOLD):
    """Hypothesis with highest average cosine similarity to the others; None if below threshold."""
    E = _embed(hyps)
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    avg = [sum(dot(E[i], E[j]) for j in range(len(E)) if j != i) / (len(E) - 1) for i in range(len(E))]
    best = max(range(len(E)), key=avg.__getitem__)
    return (hyps[best], avg[best]) if avg[best] >= thr else (None, avg[best])

def _none_missing(c): return "no information is missing" in c.lower()

def _identify(q, ctx):
    with ThreadPoolExecutor(N_SAMPLES) as ex:
        hyps = list(ex.map(lambda _: llm.ask("identify", q, ctx, temp=TEMP), range(N_SAMPLES)))
    claim, score = consensus(hyps)
    return hyps, claim, score

def predict(method, q, ctx, hyps_tuple=None):
    if method == "autorater":
        a = llm.ask("autorater", q, ctx)
        return {"pred": "Sufficient" if a.strip().upper().startswith("SUFFICIENT") else "Insufficient", "detail": a}
    if method == "migres":
        a = llm.ask("migres", q, ctx)
        return {"pred": "Insufficient" if "unanswerable" in a.lower() else "Sufficient", "detail": a}
    hyps, claim, score = hyps_tuple if hyps_tuple is not None else _identify(q, ctx)
    out = {"hypotheses": hyps, "consensus": claim, "similarity": round(score, 3)}
    if method == "identify_only":
        out["pred"] = "Sufficient" if claim and _none_missing(claim) else "Insufficient"
    else:
        if claim is None: out["pred"] = "Insufficient"; out["verification"] = "No consensus -> Insufficient"
        elif _none_missing(claim): out["pred"] = "Sufficient"; out["verification"] = "Nothing missing"
        else:
            v = llm.ask("verify", q, ctx, claim=claim)
            out["verification"] = v
            out["pred"] = "Sufficient" if v.strip().upper().startswith("YES") else "Insufficient"
    return out

def build_cases(s):
    """Full context = Sufficient. Removing a gold passage = Insufficient (as in the paper)."""
    full = s["gold"] + s["distractors"]
    ablated = s["gold"][1:] + s["distractors"]
    fmt = lambda ps: "\n".join(f"[{p['title']}] {p['text']}" for p in ps)
    return [("Sufficient", "full context", fmt(full)),
            ("Insufficient", f"removed gold passage '{s['gold'][0]['title']}'", fmt(ablated))]

def run(samples, methods):
    cases, correct = [], {m: 0 for m in methods}
    for s in samples:
        for gold, desc, ctx in build_cases(s):
            res = {}
            shared_identify = None
            if "identify_only" in methods or "identify_verify" in methods:
                shared_identify = _identify(s["question"], ctx)
            for m in methods:
                r = predict(m, s["question"], ctx, hyps_tuple=shared_identify)
                r["correct"] = r["pred"] == gold
                correct[m] += 1 if r["correct"] else 0
                res[m] = r
            cases.append({"sample_id": s.get("id"), "question": s["question"], "answer": s["answer"],
                          "setting": desc, "gold_label": gold, "context": ctx, "results": res})
    n = len(cases) or 1
    return {"accuracy": {m: round(100 * correct[m] / n, 1) for m in methods}, "n_cases": len(cases)}, cases

