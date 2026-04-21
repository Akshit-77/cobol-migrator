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
      <div className="card">
        <h3>Repository Summary</h3>
        <div className="metric-row">
          <div className="metric">
            <span className="metric-label">Total files</span>
            <span className="metric-value">{total_files}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Completed</span>
            <span className="metric-value" style={{ color: '#3fb950' }}>{completed_files}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Failed</span>
            <span className="metric-value" style={{ color: failed_files > 0 ? '#f85149' : '#3fb950' }}>{failed_files}</span>
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

      <div className="card">
        <h3>Files</h3>
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
                <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{f.file_path || '—'}</td>
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
        <div className="card">
          <h3>Unresolved References</h3>
          <p style={{ fontSize: '0.85rem', color: '#8b949e', marginBottom: 10 }}>
            These cross-file dependencies could not be resolved automatically and need manual attention.
          </p>
          {unresolved_copies.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <strong style={{ fontSize: '0.82rem', color: '#d29922' }}>COPY statements</strong>
              <ul className="lint-list" style={{ marginTop: 4 }}>
                {unresolved_copies.map(r => <li key={r}>{r}</li>)}
              </ul>
            </div>
          )}
          {unresolved_calls.length > 0 && (
            <div>
              <strong style={{ fontSize: '0.82rem', color: '#d29922' }}>CALL statements</strong>
              <ul className="lint-list" style={{ marginTop: 4 }}>
                {unresolved_calls.map(r => <li key={r}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </>
  )
}
