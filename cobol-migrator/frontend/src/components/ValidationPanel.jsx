function confidenceBadge(score) {
  if (score >= 0.8) return 'badge-green'
  if (score >= 0.5) return 'badge-yellow'
  return 'badge-red'
}

export default function ValidationPanel({ result }) {
  const { test_results, lint_results, confidence_score, iteration_count } = result

  return (
    <div className="card">
      <h3>Validation</h3>
      <div className="metric-row">
        <div className="metric">
          <span className="metric-label">Confidence</span>
          <span className="metric-value">
            <span className={`badge ${confidenceBadge(confidence_score)}`}>
              {(confidence_score * 100).toFixed(0)}%
            </span>
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Tests</span>
          <span className="metric-value">
            {test_results.passed}/{test_results.total}
            {' '}
            <span className={`badge ${test_results.failed === 0 ? 'badge-green' : 'badge-red'}`}>
              {test_results.failed === 0 ? 'all pass' : `${test_results.failed} failed`}
            </span>
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Iterations</span>
          <span className="metric-value">{iteration_count}</span>
        </div>
        <div className="metric">
          <span className="metric-label">Lint warnings</span>
          <span className="metric-value">{lint_results.length}</span>
        </div>
      </div>

      {lint_results.length > 0 && (
        <>
          <h3 style={{ marginTop: 8 }}>Lint Warnings</h3>
          <ul className="lint-list">
            {lint_results.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </>
      )}
    </div>
  )
}
