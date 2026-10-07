import { useEffect, useState } from "react";
import { fetchSnapshots, downloadUrl } from "../api/snapshots";

function humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}


export default function SnapshotsPage() {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const snaps = await fetchSnapshots();
      setSnapshots(snaps);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <h1>Snapshots</h1>
        <p>
          Timestamped archives of the full corpus assessment, generated automatically on the 1st of
          each month — download any run, same as KGHeartBeat's own periodic archive. Snapshots are
          produced only by the scheduled monthly job, not on demand, to keep the underlying FAIR
          tools and external catalogs from being queried on request.
        </p>
      </header>

      {error && <p className="input-panel__error">{error}</p>}

      <h3 style={{ marginTop: "24px" }}>Archive — Index of /snapshots/</h3>
      {loading ? (
        <p className="view-panel__note">Loading…</p>
      ) : (
        <div className="score-table-wrap">
          <table className="score-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Last modified</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.length === 0 && (
                <tr>
                  <td colSpan={3} className="view-panel__note">
                    No snapshots yet.
                  </td>
                </tr>
              )}
              {snapshots.map((s) => (
                <tr key={s.filename}>
                  <td>
                    <a href={downloadUrl(s.filename)}>{s.filename}</a>
                  </td>
                  <td>{s.modified_at.slice(0, 16).replace("T", " ")}</td>
                  <td>{humanSize(s.size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
