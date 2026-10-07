import { useEffect, useState } from "react";
import { fetchSparqlSchema, runSparqlQuery, sparqlCsvUrl } from "../api/sparql";

const DEFAULT_QUERY = `PREFIX fair: <https://fair-multi-assessor.local/schema#>
SELECT ?id ?category ?consensusScore WHERE {
  ?ds fair:id ?id ; fair:category ?category ; fair:consensusScore ?consensusScore .
}
ORDER BY DESC(?consensusScore)
LIMIT 20`;


function datasetLookupQuery(id) {
  const escaped = id.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  return `PREFIX fair: <https://fair-multi-assessor.local/schema#>
SELECT ?id ?category ?repository ?fuji ?fairchecker ?kgheartbeat ?consensusScore ?consensusAgreement WHERE {
  ?ds fair:id "${escaped}" ;
      fair:id ?id ;
      fair:category ?category .
  OPTIONAL { ?ds fair:repository ?repository }
  OPTIONAL { ?ds fair:fujiComposite ?fuji }
  OPTIONAL { ?ds fair:faircheckerComposite ?fairchecker }
  OPTIONAL { ?ds fair:kgheartbeatComposite ?kgheartbeat }
  OPTIONAL { ?ds fair:consensusScore ?consensusScore }
  OPTIONAL { ?ds fair:consensusAgreement ?consensusAgreement }
}`;
}

export default function SparqlPage() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [schema, setSchema] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lookupId, setLookupId] = useState("");

  useEffect(() => {
    fetchSparqlSchema().then(setSchema).catch(() => {});
  }, []);

  function runQuery(q = query) {
    setLoading(true);
    setError("");
    runSparqlQuery(q)
      .then(setResult)
      .catch((e) => setError(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }

  function lookupDataset(e) {
    e.preventDefault();
    if (!lookupId.trim()) return;
    const q = datasetLookupQuery(lookupId.trim());
    setQuery(q);
    runQuery(q);
  }

  return (
    <div className="sparql-page">
      <header className="fair-results__header">
        <h1>SPARQL Endpoint</h1>
      </header>

      <form className="sparql-lookup" onSubmit={lookupDataset}>
        <label htmlFor="sparql-lookup-id">Look up a single dataset's FAIR score</label>
        <div className="sparql-lookup__row">
          <input
            id="sparql-lookup-id"
            type="text"
            placeholder="Enter a dataset id…"
            value={lookupId}
            onChange={(e) => setLookupId(e.target.value)}
          />
          <button type="submit" disabled={loading || !lookupId.trim()}>
            {loading ? "Looking up…" : "🔎 Look up"}
          </button>
        </div>
      </form>

      <div className="sparql-layout">
        <div className="sparql-main">
          <textarea
            className="sparql-editor"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            spellCheck={false}
            rows={12}
          />

          <div className="sparql-controls">
            <button className="sparql-run" onClick={() => runQuery()} disabled={loading}>
              {loading ? "Running…" : "▶ Run query"}
            </button>
            <a
              className="sparql-download"
              href={sparqlCsvUrl(query)}
              download="sparql_results.csv"
            >
              ⬇ Download CSV
            </a>
          </div>

          {error && <p className="input-panel__error">{error}</p>}

          {result && (
            <>
              <p className="view-panel__note">{result.count} result{result.count === 1 ? "" : "s"}</p>
              <div className="score-table-wrap">
                <table className="score-table">
                  <thead>
                    <tr>
                      {result.columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((val, j) => (
                          <td key={j}>{val === "" ? "—" : val}</td>
                        ))}
                      </tr>
                    ))}
                    {result.rows.length === 0 && (
                      <tr>
                        <td colSpan={result.columns.length || 1} className="view-panel__note" style={{ textAlign: "center", padding: 24 }}>
                          No matches.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {schema && (
          <aside className="sparql-sidebar">
            <div className="sparql-sidebar__section">
              <div className="fair-sidebar__title">Prefixes</div>
              {Object.entries(schema.prefixes).map(([p, uri]) => (
                <div key={p} className="sparql-prefix">
                  <code>{p}:</code> {uri}
                </div>
              ))}
            </div>

            <div className="sparql-sidebar__section">
              <div className="fair-sidebar__title">Predicates</div>
              {schema.predicates.map((p) => (
                <div key={p.predicate} className="sparql-predicate">
                  <code>{p.predicate}</code>
                  <span>{p.description}</span>
                </div>
              ))}
            </div>

            <div className="sparql-sidebar__section">
              <div className="fair-sidebar__title">Example queries</div>
              {schema.example_queries.map((ex) => (
                <button key={ex.label} className="sparql-example" onClick={() => setQuery(ex.query)}>
                  {ex.label}
                </button>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
