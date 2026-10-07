import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { explain } from "../api/client";


export default function AIExplanation({ consensus, toolResults }) {
  const [open, setOpen] = useState(true);
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fetchExplanation() {
    setLoading(true);
    setError("");
    try {
      const data = await explain(consensus, toolResults);
      setText(data.explanation);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Failed to generate explanation.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ai-explanation">
      <div className="ai-explanation__header" onClick={() => setOpen((o) => !o)}>
        <h3>AI Explanation</h3>
        <span className="ai-explanation__toggle">{open ? "▾" : "▸"}</span>
      </div>

      {open && (
        <div className="ai-explanation__body">
          {text == null && !loading && (
            <button className="ai-explanation__generate" onClick={fetchExplanation}>
              Generate Explanation
            </button>
          )}
          {loading && <p>Generating explanation…</p>}
          {error && <p className="input-panel__error">{error}</p>}
          {text != null && (
            <>
              <div className="ai-explanation__markdown">
                <ReactMarkdown>{text}</ReactMarkdown>
              </div>
              <button className="ai-explanation__generate" onClick={fetchExplanation} disabled={loading}>
                Regenerate
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
