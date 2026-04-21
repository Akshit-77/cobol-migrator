import { render, screen } from '@testing-library/react'
import RepoPanel from '../components/RepoPanel'

const baseResult = {
  total_files: 3,
  completed_files: 2,
  failed_files: 1,
  average_confidence: 0.75,
  files: [
    { file_path: 'src/prog1.cbl', status: 'done', confidence_score: 0.9, test_results: { passed: 3, total: 3 }, iteration_count: 1 },
    { file_path: 'src/prog2.cbl', status: 'done', confidence_score: 0.6, test_results: { passed: 2, total: 3 }, iteration_count: 2 },
    { file_path: 'src/prog3.cbl', status: 'failed', confidence_score: 0, test_results: { passed: 0, total: 0 }, iteration_count: 3 },
  ],
  unresolved_copies: [],
  unresolved_calls: [],
}

describe('RepoPanel', () => {
  it('shows total file count in summary', () => {
    render(<RepoPanel result={baseResult} />)
    // The metric value spans are within .metric divs; there may be multiple "3"s in the table too
    const metrics = document.querySelectorAll('.metric-value')
    const texts = Array.from(metrics).map(m => m.textContent.trim())
    expect(texts).toContain('3')
  })

  it('shows completed count in summary', () => {
    render(<RepoPanel result={baseResult} />)
    const metrics = document.querySelectorAll('.metric-value')
    const texts = Array.from(metrics).map(m => m.textContent.trim())
    expect(texts).toContain('2')
  })

  it('shows failed count in summary', () => {
    render(<RepoPanel result={baseResult} />)
    const metrics = document.querySelectorAll('.metric-value')
    const texts = Array.from(metrics).map(m => m.textContent.trim())
    expect(texts).toContain('1')
  })

  it('shows average confidence', () => {
    render(<RepoPanel result={baseResult} />)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('renders file paths in table', () => {
    render(<RepoPanel result={baseResult} />)
    expect(screen.getByText('src/prog1.cbl')).toBeInTheDocument()
    expect(screen.getByText('src/prog3.cbl')).toBeInTheDocument()
  })

  it('does not show unresolved section when empty', () => {
    render(<RepoPanel result={baseResult} />)
    expect(screen.queryByText(/unresolved references/i)).not.toBeInTheDocument()
  })

  it('shows unresolved COPY refs when present', () => {
    render(<RepoPanel result={{ ...baseResult, unresolved_copies: ['CUSTDATA', 'ACCTDATA'] }} />)
    expect(screen.getByText(/unresolved references/i)).toBeInTheDocument()
    expect(screen.getByText('CUSTDATA')).toBeInTheDocument()
  })

  it('shows unresolved CALL refs when present', () => {
    render(<RepoPanel result={{ ...baseResult, unresolved_calls: ['SUBPROG1'] }} />)
    expect(screen.getByText('SUBPROG1')).toBeInTheDocument()
  })
})
