import { useState } from 'react'

const TABS = ['Paste Code', 'File URL', 'Repo URL']

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

  const disabled = loading || (tab === 0 ? !code.trim() : tab === 1 ? !fileUrl.trim() : !repoUrl.trim())

  return (
    <div className="card">
      <div className="tabs">
        {TABS.map((t, i) => (
          <button key={t} className={`tab ${tab === i ? 'active' : ''}`} onClick={() => setTab(i)}>
            {t}
          </button>
        ))}
      </div>

      {tab === 0 && (
        <textarea
          rows={12}
          placeholder="Paste COBOL source code here..."
          value={code}
          onChange={e => setCode(e.target.value)}
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

      <div style={{ marginTop: 12 }}>
        <button className="btn-primary" onClick={handleSubmit} disabled={disabled}>
          {loading ? 'Migrating…' : 'Migrate to Python 3'}
        </button>
      </div>
    </div>
  )
}
