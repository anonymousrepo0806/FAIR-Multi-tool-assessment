import { useState } from "react";
import { invalidDatasetUrlReason } from "../lib/datasetUrlGuard";


export default function InputPanel({ onSubmit, loading }) {
  const [mode, setMode] = useState("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [runFuji, setRunFuji] = useState(true);
  const [runFairchecker, setRunFairchecker] = useState(true);
  const [runKgheartbeat, setRunKgheartbeat] = useState(true);
  const [error, setError] = useState("");

  function isValidUrl(value) {
    try {
      const u = new URL(value);
      return u.protocol === "http:" || u.protocol === "https:";
    } catch {
      return false;
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!runFuji && !runFairchecker && !runKgheartbeat) {
      setError("Select at least one tool to run.");
      return;
    }

    if (mode === "url") {
      if (!isValidUrl(url)) {
        setError("Please enter a valid http(s) URL.");
        return;
      }
      const reason = invalidDatasetUrlReason(url);
      if (reason) {
        setError(reason);
        return;
      }
      onSubmit({ type: "url", value: url, tools: { runFuji, runFairchecker, runKgheartbeat } });
    } else {
      if (!file) {
        setError("Please choose a .csv or .json file.");
        return;
      }
      const okType = /\.(csv|json)$/i.test(file.name);
      if (!okType) {
        setError("Unsupported file type — please upload a .csv or .json file.");
        return;
      }
      onSubmit({ type: "file", value: file, tools: { runFuji, runFairchecker, runKgheartbeat } });
    }
  }

  return (
    <form className="input-panel" onSubmit={handleSubmit}>
      <div className="input-panel__mode-toggle">
        <button
          type="button"
          className={mode === "url" ? "active" : ""}
          onClick={() => setMode("url")}
        >
          Enter URL
        </button>
        <button
          type="button"
          className={mode === "file" ? "active" : ""}
          onClick={() => setMode("file")}
        >
          Upload File
        </button>
      </div>

      {mode === "url" ? (
        <input
          type="text"
          placeholder="https://your-repository.org/dataset/123 (a dataset link, not a generic site like wikidata.org or google.com)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="input-panel__url"
        />
      ) : (
        <input
          type="file"
          accept=".csv,.json"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="input-panel__file"
        />
      )}

      <div className="input-panel__tools">
        <label>
          <input type="checkbox" checked={runFuji} onChange={(e) => setRunFuji(e.target.checked)} />
          F-UJI
        </label>
        <label>
          <input
            type="checkbox"
            checked={runFairchecker}
            onChange={(e) => setRunFairchecker(e.target.checked)}
          />
          FAIR Checker
        </label>
        <label>
          <input
            type="checkbox"
            checked={runKgheartbeat}
            onChange={(e) => setRunKgheartbeat(e.target.checked)}
          />
          KG Heartbeat
        </label>
      </div>

      {error && <p className="input-panel__error">{error}</p>}

      <button type="submit" disabled={loading} className="input-panel__submit">
        {loading ? "Assessing…" : "Assess"}
      </button>
    </form>
  );
}
