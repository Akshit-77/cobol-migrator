import { useState } from 'react'

const TABS = [
  { label: 'Paste Code', key: 'code' },
  { label: 'File URL',   key: 'url' },
  { label: 'Repo URL',   key: 'repo' },
]

export default function InputPanel({ onSubmit, loading }) {
  const [tab, setTab] = useState(0)
  const [code, setCode] = useState('')
  const [fileUrl, setFileUrl] = useState('')
  const [repoUrl, setRepoUrl] = useState('')

  function handleSubmit() {
    if (tab === 0) onSubmit({ source_code: code })
    else if (tab === 1) onSubmit({ source_url: fileUrl })
    else onSubmit({ repo_url: repoUrl })
  }

  const disabled = loading || (
    tab === 0 ? !code.trim() :
    tab === 1 ? !fileUrl.trim() :
    !repoUrl.trim()
  )

  const hints = [
    'Paste raw COBOL source — IDENTIFICATION, WORKING-STORAGE, PROCEDURE DIVISION',
    'https://github.com/owner/repo/blob/main/program.cbl',
    'https://github.com/owner/repo — migrates all .cbl / .cob / .cobol files',
  ]

  return (
    <div className="card">
      <div className="tabs">
        {TABS.map((t, i) => (
          <button
            key={t.key}
            className={`tab ${tab === i ? 'active' : ''}`}
            onClick={() => setTab(i)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 0 && (
        <textarea
          rows={14}
          placeholder="Paste COBOL source code here..."
          value={code}
          onChange={e => setCode(e.target.value)}
          spellCheck={false}
        />
      )}
      {tab === 1 && (
        <input
          type="text"
          placeholder="https://github.com/owner/repo/blob/main/program.cbl"
          value={fileUrl}
          onChange={e => setFileUrl(e.target.value)}
        />
      )}
      {tab === 2 && (
        <input
          type="text"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={e => setRepoUrl(e.target.value)}
        />
      )}

      <div className="input-submit-row">
        <span className="input-hint">{hints[tab]}</span>
        <button
          className={`btn-primary ${loading ? 'loading-state' : ''}`}
          onClick={handleSubmit}
          disabled={disabled}
        >
          {loading ? '◌ MIGRATING…' : 'MIGRATE →'}
        </button>
      </div>
    </div>
  )
}
