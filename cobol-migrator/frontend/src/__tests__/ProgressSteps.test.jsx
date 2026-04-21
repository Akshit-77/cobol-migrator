import { render, screen } from '@testing-library/react'
import ProgressSteps from '../components/ProgressSteps'

describe('ProgressSteps', () => {
  it('renders all 4 step labels', () => {
    render(<ProgressSteps status="parsing" />)
    expect(screen.getByText('Parse COBOL')).toBeInTheDocument()
    expect(screen.getByText('Translate')).toBeInTheDocument()
    expect(screen.getByText('Validate & Test')).toBeInTheDocument()
    expect(screen.getByText('Generate Report')).toBeInTheDocument()
  })

  it('shows parse as running when status is parsing', () => {
    const { container } = render(<ProgressSteps status="parsing" />)
    const steps = container.querySelectorAll('.step')
    expect(steps[0].classList.contains('step-running')).toBe(true)
    expect(steps[1].classList.contains('step-pending')).toBe(true)
  })

  it('shows parse as done and translate as running when translating', () => {
    const { container } = render(<ProgressSteps status="translating" />)
    const steps = container.querySelectorAll('.step')
    expect(steps[0].classList.contains('step-done')).toBe(true)
    expect(steps[1].classList.contains('step-running')).toBe(true)
    expect(steps[2].classList.contains('step-pending')).toBe(true)
  })

  it('shows parse+translate done and validate running when validating', () => {
    const { container } = render(<ProgressSteps status="validating" />)
    const steps = container.querySelectorAll('.step')
    expect(steps[0].classList.contains('step-done')).toBe(true)
    expect(steps[1].classList.contains('step-done')).toBe(true)
    expect(steps[2].classList.contains('step-running')).toBe(true)
    expect(steps[3].classList.contains('step-pending')).toBe(true)
  })

  it('returns null when status is done', () => {
    const { container } = render(<ProgressSteps status="done" />)
    expect(container.firstChild).toBeNull()
  })

  it('returns null when status is null', () => {
    const { container } = render(<ProgressSteps status={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows retry label on validate step when iterationCount > 1', () => {
    render(<ProgressSteps status="validating" iterationCount={2} maxIterations={3} />)
    expect(screen.getByText(/retry/i)).toBeInTheDocument()
  })

  it('does not show retry label on first iteration', () => {
    render(<ProgressSteps status="validating" iterationCount={1} maxIterations={3} />)
    expect(screen.queryByText(/retry/i)).not.toBeInTheDocument()
  })
})
