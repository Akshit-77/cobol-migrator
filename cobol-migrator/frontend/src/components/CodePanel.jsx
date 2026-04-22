export default function CodePanel({ original, translated }) {
  return (
    <div className="code-split">
      <div className="code-pane">
        <div className="code-titlebar">
          <div className="traffic-lights">
            <div className="traffic-dot td-red" />
            <div className="traffic-dot td-yellow" />
            <div className="traffic-dot td-green" />
          </div>
          <span className="code-filename">source.cbl</span>
          <span className="code-lang-badge lang-cobol">COBOL</span>
        </div>
        <div className="code-scroll">
          <pre><code>{original || '—'}</code></pre>
        </div>
      </div>

      <div className="code-pane">
        <div className="code-titlebar">
          <div className="traffic-lights">
            <div className="traffic-dot td-red" />
            <div className="traffic-dot td-yellow" />
            <div className="traffic-dot td-green" />
          </div>
          <span className="code-filename">translated.py</span>
          <span className="code-lang-badge lang-python">Python</span>
        </div>
        <div className="code-scroll">
          <pre><code>{translated || '—'}</code></pre>
        </div>
      </div>
    </div>
  )
}
