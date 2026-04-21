import { render, screen } from '@testing-library/react'
import ValidationPanel from '../components/ValidationPanel'

const baseResult = {
  test_results: { passed: 4, failed: 0, errors: [], total: 4 },
  lint_results: [],
  confidence_score: 1.0,
  iteration_count: 1,
}

describe('ValidationPanel', () => {
  it('shows confidence score', () => {
    render(<ValidationPanel result={baseResult} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('shows test pass count', () => {
    render(<ValidationPanel result={baseResult} />)
    expect(screen.getByText(/4\/4/)).toBeInTheDocument()
  })

  it('shows all pass badge when no failures', () => {
    render(<ValidationPanel result={baseResult} />)
    expect(screen.getByText('all pass')).toBeInTheDocument()
  })

  it('shows failed badge when tests fail', () => {
    render(<ValidationPanel result={{ ...baseResult, test_results: { passed: 1, failed: 2, errors: [], total: 3 } }} />)
    expect(screen.getByText('2 failed')).toBeInTheDocument()
  })

  it('shows iteration count', () => {
    render(<ValidationPanel result={baseResult} />)
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('shows lint warnings when present', () => {
    render(<ValidationPanel result={{ ...baseResult, lint_results: ['line 5: unused import'] }} />)
    expect(screen.getByText('line 5: unused import')).toBeInTheDocument()
  })

  it('does not show lint list when clean', () => {
    render(<ValidationPanel result={baseResult} />)
    // The metric label "Lint warnings" is always shown; the list below it is not
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })
})
