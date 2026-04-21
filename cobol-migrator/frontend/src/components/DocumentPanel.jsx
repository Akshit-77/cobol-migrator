import ReactMarkdown from 'react-markdown'

export default function DocumentPanel({ documentation }) {
  if (!documentation) return null
  return (
    <div className="card">
      <h3>Migration Report</h3>
      <div className="markdown-body">
        <ReactMarkdown>{documentation}</ReactMarkdown>
      </div>
    </div>
  )
}
