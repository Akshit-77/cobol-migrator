const LABELS = {
  queued:      'Queued — waiting to start',
  starting:    'Starting pipeline…',
  parsing:     'Parsing COBOL structure…',
  translating: 'Translating to Python 3…',
  validating:  'Running validation & tests…',
  done:        'Migration complete',
  failed:      'Migration failed',
}

export default function StatusBar({ status }) {
  return (
    <div className="status-bar">
      <div className={`dot dot-${status}`} />
      <span>{LABELS[status] ?? status}</span>
    </div>
  )
}
