export default function CodePanel({ original, translated }) {
  return (
    <div className="code-split">
      <div>
        <h3>Original COBOL</h3>
        <div className="code-block">
          <div className="code-block-label">COBOL</div>
          <pre><code>{original || '—'}</code></pre>
        </div>
      </div>
      <div>
        <h3>Translated Python 3</h3>
        <div className="code-block">
          <div className="code-block-label">Python</div>
          <pre><code>{translated || '—'}</code></pre>
        </div>
      </div>
    </div>
  )
}
