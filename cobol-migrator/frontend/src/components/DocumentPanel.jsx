import ReactMarkdown from 'react-markdown'

export default function DocumentPanel({ documentation }) {
  if (!documentation) return null
  return (
    <div className="card">
      <div className="panel-header">
        <span className="panel-accent panel-accent-amber" />
        <span className="panel-title">Migration Report</span>
      </div>
      <div className="markdown-body">
        <ReactMarkdown>{documentation}</ReactMarkdown>
      </div>
    </div>
  )
}
