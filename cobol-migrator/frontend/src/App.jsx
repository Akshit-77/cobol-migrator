import { useState, useEffect, useRef } from 'react'
import { submitMigration, getStatus } from './api'
import InputPanel from './components/InputPanel'
import StatusBar from './components/StatusBar'
import ProgressSteps from './components/ProgressSteps'
import CodePanel from './components/CodePanel'
import ValidationPanel from './components/ValidationPanel'
import DocumentPanel from './components/DocumentPanel'
import RepoPanel from './components/RepoPanel'
import './index.css'

const TERMINAL_STATUSES = new Set(['done', 'failed'])

export default function App() {
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sourceCode, setSourceCode] = useState('')
  const [isRepo, setIsRepo] = useState(false)
  const pollRef = useRef(null)

  function stopPolling() {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => () => stopPolling(), [])

  async function handleSubmit(payload) {
    stopPolling()
    setLoading(true)
    setError(null)
    setResult(null)
    setStatus('queued')
    setIsRepo(!!payload.repo_url)
    setSourceCode(payload.source_code || '')

    try {
      const { job_id } = await submitMigration(payload)
      setJobId(job_id)

      pollRef.current = setInterval(async () => {
        try {
          const data = await getStatus(job_id)
          setStatus(data.status)
          if (data.result) setResult(data.result)
          if (data.error) setError(data.error)
          if (TERMINAL_STATUSES.has(data.status)) {
            stopPolling()
            setLoading(false)
          }
        } catch {
          stopPolling()
          setLoading(false)
          setError('Lost connection to server.')
        }
      }, 2000)
    } catch (e) {
      setLoading(false)
      setStatus(null)
      setError(e?.response?.data?.detail || e.message || 'Submission failed.')
    }
  }

  const isTerminal = TERMINAL_STATUSES.has(status)
  const isDone = status === 'done' && result
  const iterationCount = result?.iteration_count ?? 0
  const maxIterations = result?.max_iterations ?? 3

  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <div className="header-logo">
            <span className="logo-cobol">COBOL</span>
            <span className="logo-arrow">→</span>
            <span className="logo-python">PYTHON 3</span>
          </div>
          <div className="header-meta">
            <span className="meta-tag">IE624</span>
            <span className="meta-sep">·</span>
            <span className="meta-tag">IIT BOMBAY</span>
            <span className="meta-sep">·</span>
            <span className="meta-tag">AGENTIC AI</span>
          </div>
        </div>
      </header>

      <InputPanel onSubmit={handleSubmit} loading={loading} />

      {error && <div className="error-box">{error}</div>}

      {status && !isTerminal && (
        <ProgressSteps
          status={status}
          iterationCount={iterationCount}
          maxIterations={maxIterations}
        />
      )}

      {isTerminal && <StatusBar status={status} />}

      {isDone && !isRepo && (
        <>
          <CodePanel original={result.source_code || sourceCode} translated={result.translated_code} />
          <ValidationPanel result={result} />
          <DocumentPanel documentation={result.documentation} />
        </>
      )}

      {isDone && isRepo && <RepoPanel result={result} />}

      {status === 'failed' && result?.error_log?.length > 0 && (
        <div className="card">
          <div className="panel-header">
            <span className="panel-accent" style={{ background: 'var(--red)' }} />
            <span className="panel-title">Error Log</span>
          </div>
          <ul className="lint-list">
            {result.error_log.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </>
  )
}
