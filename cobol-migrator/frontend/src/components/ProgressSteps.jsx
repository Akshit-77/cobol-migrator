const STEPS = [
  { key: 'parse',     label: 'Parse COBOL',       sub: 'Extract paragraphs & variables' },
  { key: 'translate', label: 'Translate',          sub: 'Generate Python 3 code' },
  { key: 'validate',  label: 'Validate & Test',    sub: 'Lint, syntax, run tests' },
  { key: 'document',  label: 'Generate Report',    sub: 'Confidence score & mapping' },
]

// Map pipeline status → which step is active and which are done
function resolveSteps(status, iterationCount, maxIterations) {
  const order = ['parse', 'translate', 'validate', 'document']
  const activeIdx = {
    queued: -1, starting: -1,
    parsing: 0,
    translating: 1,
    validating: 2,
    done: 4, failed: 4,
  }[status] ?? -1

  return STEPS.map((step, i) => {
    let state = 'pending'
    if (status === 'done')        state = 'done'
    else if (status === 'failed') state = i <= activeIdx - 1 ? 'done' : i === activeIdx ? 'failed' : 'pending'
    else if (i < activeIdx)       state = 'done'
    else if (i === activeIdx)     state = 'running'

    const isValidating = step.key === 'validate' && state === 'running' && iterationCount > 1
    const sub = isValidating
      ? `Retry ${iterationCount - 1}/${maxIterations - 1} — fixing errors`
      : step.sub

    return { ...step, state, sub }
  })
}

function Icon({ state }) {
  if (state === 'done')    return <span className="step-icon step-done">✓</span>
  if (state === 'running') return <span className="step-icon step-running"><span className="spinner" /></span>
  if (state === 'failed')  return <span className="step-icon step-failed">✗</span>
  return <span className="step-icon step-pending" />
}

export default function ProgressSteps({ status, iterationCount = 0, maxIterations = 3 }) {
  if (!status || status === 'done') return null
  const steps = resolveSteps(status, iterationCount, maxIterations)

  return (
    <div className="progress-steps card">
      {steps.map((step, i) => (
        <div key={step.key} className={`step step-${step.state}`}>
          <div className="step-left">
            <Icon state={step.state} />
            {i < steps.length - 1 && <div className={`step-line ${step.state === 'done' ? 'line-done' : ''}`} />}
          </div>
          <div className="step-body">
            <span className="step-label">{step.label}</span>
            <span className="step-sub">{step.sub}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
