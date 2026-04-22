function confidenceBadge(score) {
  if (score >= 0.8) return 'badge-green'
  if (score >= 0.5) return 'badge-yellow'
  return 'badge-red'
}

export default function RepoPanel({ result }) {
  const {
    total_files, completed_files, failed_files,
    average_confidence, files = [],
    unresolved_copies = [], unresolved_calls = [],
  } = result

  return (
    <>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="repo-summary">
          <div className="metric">
            <span className="metric-label">Total files</span>
            <span className="metric-value">{total_files}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Completed</span>
            <span className="metric-value" style={{ color: 'var(--teal)' }}>{completed_files}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Failed</span>
            <span className="metric-value" style={{ color: failed_files > 0 ? 'var(--red)' : 'var(--teal)' }}>
              {failed_files}
            </span>
          </div>
          <div className="metric">
            <span className="metric-label">Avg confidence</span>
            <span className="metric-value">
              <span className={`badge ${confidenceBadge(average_confidence)}`}>
                {(average_confidence * 100).toFixed(0)}%
              </span>
            </span>
          </div>
        </div>
      </div>

      <div className="repo-table-wrap">
        <table className="repo-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Tests</th>
              <th>Iterations</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f, i) => (
              <tr key={i}>
                <td className="file-path">{f.file_path || '—'}</td>
                <td>
                  <span className={`badge ${f.status === 'done' ? 'badge-green' : 'badge-red'}`}>
                    {f.status}
                  </span>
                </td>
                <td>
                  <span className={`badge ${confidenceBadge(f.confidence_score ?? 0)}`}>
                    {((f.confidence_score ?? 0) * 100).toFixed(0)}%
                  </span>
                </td>
                <td>{f.test_results?.passed ?? 0}/{f.test_results?.total ?? 0}</td>
                <td>{f.iteration_count ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(unresolved_copies.length > 0 || unresolved_calls.length > 0) && (
        <div className="card unresolved-card">
          <div className="panel-header">
            <span className="panel-accent panel-accent-amber" />
            <span className="panel-title">Unresolved References</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-mid)', marginBottom: 16 }}>
            Cross-file dependencies not resolved automatically — require manual review.
          </p>
          {unresolved_copies.length > 0 && (
            <div className="unresolved-group">
              <div className="unresolved-group-label">COPY Statements</div>
              <ul className="lint-list">
                {unresolved_copies.map(r => <li key={r}>{r}</li>)}
              </ul>
            </div>
          )}
          {unresolved_calls.length > 0 && (
            <div className="unresolved-group">
              <div className="unresolved-group-label">CALL Statements</div>
              <ul className="lint-list">
                {unresolved_calls.map(r => <li key={r}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </>
  )
}
