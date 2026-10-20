import { useEffect, useState } from "react";

const LABELS = { autorater: "Autorater", migres: "MIGRES", identify_only: "Identify-only", identify_verify: "Identify-then-Verify" };

export default function App() {
  const [health, setHealth] = useState(null);
  const [samples, setSamples] = useState([]);
  const [picked, setPicked] = useState([]);
  const [methods, setMethods] = useState(Object.keys(LABELS));
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    fetch("/api/health/").then(r => r.json()).then(setHealth).catch(() => setError("Backend not reachable on :8000"));
    fetch("/api/samples/").then(r => r.json()).then(d => { setSamples(d.samples); setPicked(d.samples.map(s => s.id)); });
  }, []);

  const toggle = (list, set, v) => set(list.includes(v) ? list.filter(x => x !== v) : [...list, v]);

  async function run() {
    setBusy(true); setError(""); setResult(null);
    try {
      const r = await fetch("/api/evaluate/", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_ids: picked, methods }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Request failed");
      setResult(d);
    } catch (e) { setError(e.message); }
    setBusy(false);
  }

  return (
    <main>
      <h1>Information Sufficiency Evaluator</h1>
      <p className="sub">Tests the Identify-then-Verify framework (Jain &amp; Garimella, EACL 2026) on HotpotQA-style questions.</p>
      {health && <p className={"badge " + health.llm_mode}>LLM mode: {health.llm_mode}{health.llm_mode === "mock" && " (offline heuristic demo, set LLM_API_KEY for real runs)"}</p>}
      {error && <p className="err">{error}</p>}

      <section>
        <h2>1. Choose questions</h2>
        {samples.map(s => (
          <label key={s.id} className="row">
            <input type="checkbox" checked={picked.includes(s.id)} onChange={() => toggle(picked, setPicked, s.id)} />
            <span><b>{s.question}</b><br /><small>Reference answer: {s.answer}</small></span>
          </label>
        ))}
      </section>

      <section>
        <h2>2. Choose methods</h2>
        {Object.entries(LABELS).map(([k, v]) => (
          <label key={k} className="chip"><input type="checkbox" checked={methods.includes(k)} onChange={() => toggle(methods, setMethods, k)} /> {v}</label>
        ))}
      </section>

      <button onClick={run} disabled={busy || !picked.length || !methods.length}>{busy ? "Running…" : "Run evaluation"}</button>

      {result && (
        <section>
          <h2>Accuracy ({result.summary.n_cases} cases: each question with full context and with a gold passage removed)</h2>
          {Object.entries(result.summary.accuracy).map(([m, a]) => (
            <div key={m} className="bar"><span>{LABELS[m]}</span><div><i style={{ width: a + "%" }} /></div><b>{a}%</b></div>
          ))}

          <h2>Case details</h2>
          {result.cases.map((c, i) => (
            <div key={i} className="case">
              <div className="head" onClick={() => setOpen(open === i ? null : i)}>
                <span><b>{c.question}</b><br /><small>{c.setting} · expected {c.gold_label}</small></span>
                <span className="preds">{Object.entries(c.results).map(([m, r]) =>
                  <em key={m} className={r.correct ? "ok" : "bad"} title={LABELS[m]}>{LABELS[m].split("-")[0]}: {r.pred}</em>)}</span>
              </div>
              {open === i && (
                <div className="body">
                  <pre>{c.context}</pre>
                  {Object.entries(c.results).map(([m, r]) => (
                    <div key={m}><h4>{LABELS[m]} → {r.pred} {r.correct ? "✓" : "✗"}</h4>
                      {r.detail && <p>{r.detail}</p>}
                      {r.hypotheses && <ol>{r.hypotheses.map((h, j) => <li key={j}>{h}</li>)}</ol>}
                      {r.consensus !== undefined && <p><b>Consensus gap claim:</b> {r.consensus || "none (below similarity threshold)"} <small>(avg similarity {r.similarity})</small></p>}
                      {r.verification && <p><b>Verification:</b> {r.verification}</p>}
                    </div>))}
                </div>)}
            </div>))}
        </section>
      )}
    </main>
  );
}
