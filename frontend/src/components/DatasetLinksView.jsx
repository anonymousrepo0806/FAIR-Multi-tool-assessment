import ScoreValue from "./ScoreValue";

const TOOL_LABELS = { fuji: "F-UJI", fairchecker: "FAIR Checker", kgheartbeat: "KG Heartbeat" };
const CHECK_LABELS = { online: "Online", offline: "Offline", unreachable: "Unreachable" };

// The "BLOD page" link is hidden for now; the link data is kept in the API.
// To show it again, build the frontend with VITE_SHOW_BLOD_PAGE_LINK=true.
const SHOW_BLOD_PAGE_LINK = import.meta.env.VITE_SHOW_BLOD_PAGE_LINK === "true";

/**
 * Dataset access panel on the FAIR score page: the per-tool FAIR scores next to the
 * dataset link and every SPARQL endpoint that serves it.
 */
export default function DatasetLinksView({ detail }) {
  const endpoints = detail?.sparql_endpoints || [];
  const mapped = Object.fromEntries(
    Object.entries(detail?.tool_results || {}).map(([t, r]) => [t, r?.mapped?.composite ?? null])
  );
  const datasetLink = detail?.website || detail?.dataset_url;

  return (
    <div className="view-panel dataset-links">
      <h3>FAIR Score &amp; Dataset Access</h3>

      <div className="dataset-links__scores">
        {Object.entries(TOOL_LABELS).map(([tool, label]) => (
          <div key={tool} className="dataset-links__score">
            <span className="dataset-links__score-label">{label}</span>
            <ScoreValue score={mapped[tool]} />
          </div>
        ))}
        <div className="dataset-links__score dataset-links__score--consensus">
          <span className="dataset-links__score-label">Consensus</span>
          <ScoreValue score={detail?.consensus?.overall} />
        </div>
      </div>

      <dl className="dataset-links__list">
        <dt>Dataset</dt>
        <dd>
          {datasetLink ? (
            <a href={datasetLink} target="_blank" rel="noreferrer">{detail?.title || datasetLink} ↗</a>
          ) : (
            <span className="view-panel__note">No dataset link recorded</span>
          )}
          {SHOW_BLOD_PAGE_LINK && detail?.blod_page && (
            <>
              {" · "}
              <a href={detail.blod_page} target="_blank" rel="noreferrer">BLOD page ↗</a>
            </>
          )}
        </dd>

        <dt>SPARQL endpoint{endpoints.length > 1 ? "s" : ""}</dt>
        <dd>
          {endpoints.length === 0 && <span className="view-panel__note">None known for this dataset</span>}
          {endpoints.map((ep) => (
            <div key={ep.url} className="dataset-links__endpoint">
              <a href={ep.url} target="_blank" rel="noreferrer" className="dataset-links__url">{ep.url}</a>
              {ep.check && (
                <span
                  className={`endpoint-check endpoint-check--${ep.check}`}
                  title={`KGHeartBeat availability check${ep.checked_on ? ` on ${ep.checked_on}` : ""}`}
                >
                  {CHECK_LABELS[ep.check] || ep.check}
                  {ep.checked_on ? ` · ${ep.checked_on}` : ""}
                </span>
              )}
              {ep.description && <div className="dataset-links__note">{ep.description}</div>}
            </div>
          ))}
        </dd>
      </dl>
    </div>
  );
}
