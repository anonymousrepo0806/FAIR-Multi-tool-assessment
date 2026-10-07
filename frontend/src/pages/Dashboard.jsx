import { useState } from "react";
import InputPanel from "../components/InputPanel";
import ToolScoreView from "../components/ToolScoreView";
import NativeScoreView from "../components/NativeScoreView";
import ConsensusView from "../components/ConsensusView";
import AIExplanation from "../components/AIExplanation";
import { assessUrl, assessFile } from "../api/client";

const TOOL_LABELS = { fuji: "F-UJI", fairchecker: "FAIR Checker", kgheartbeat: "KG Heartbeat" };

export default function Dashboard() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [tab, setTab] = useState("mapped");

  async function handleSubmit({ type, value, tools }) {
    setLoading(true);
    setErrorMsg("");
    setResult(null);

    const running = [];
    if (tools.runFuji) running.push(TOOL_LABELS.fuji);
    if (tools.runFairchecker) running.push(TOOL_LABELS.fairchecker);
    if (tools.runKgheartbeat) running.push(TOOL_LABELS.kgheartbeat);
    setProgress(running);

    const opts = {
      runFuji: tools.runFuji,
      runFairchecker: tools.runFairchecker,
      runKgheartbeat: tools.runKgheartbeat,
    };

    try {
      const data = type === "url" ? await assessUrl(value, opts) : await assessFile(value, opts);
      setResult(data);
    } catch (e) {
      setErrorMsg(e?.response?.data?.detail || e.message || "Assessment failed.");
    } finally {
      setLoading(false);
      setProgress([]);
    }
  }

  function handleExportJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fair-assessment-result.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handlePrint() {


    window.print();
  }

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h1>Multi-Tool FAIR Assessment</h1>
      </header>

      <InputPanel onSubmit={handleSubmit} loading={loading} />

      {loading && (
        <div className="dashboard__progress">
          <p>Running: {progress.join(", ")}…</p>
        </div>
      )}

      {errorMsg && <p className="input-panel__error">{errorMsg}</p>}

      {result && (
        <>
          <div className="dashboard__input-echo">
            <strong>Input:</strong> {result.input.type === "url" ? result.input.value : `${result.input.value} (${result.input.resources_found ?? 1} resource(s) found; first used)`}
          </div>

          <div className="dashboard__tabs">
            <button className={tab === "mapped" ? "active" : ""} onClick={() => setTab("mapped")}>
              Mapped Scores
            </button>
            <button className={tab === "native" ? "active" : ""} onClick={() => setTab("native")}>
              Native Scores
            </button>
            <button className={tab === "consensus" ? "active" : ""} onClick={() => setTab("consensus")}>
              Consensus
            </button>
          </div>

          <div className="dashboard__view">
            {tab === "mapped" && <ToolScoreView toolResults={result.tool_results} />}
            {tab === "native" && <NativeScoreView toolResults={result.tool_results} />}
            {tab === "consensus" && <ConsensusView consensus={result.consensus} />}
          </div>

          <AIExplanation
            consensus={result.consensus}
            toolResults={result.tool_results}
          />

          <div className="dashboard__export">
            <button onClick={handleExportJson}>Export JSON</button>
            <button onClick={handlePrint}>Export / Print PDF</button>
          </div>
        </>
      )}
    </div>
  );
}
