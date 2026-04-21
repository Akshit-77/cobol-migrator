import { render, screen } from '@testing-library/react'
import StatusBar from '../components/StatusBar'

describe('StatusBar', () => {
  it('shows queued label', () => {
    render(<StatusBar status="queued" />)
    expect(screen.getByText(/queued/i)).toBeInTheDocument()
  })

  it('shows parsing label', () => {
    render(<StatusBar status="parsing" />)
    expect(screen.getByText(/parsing/i)).toBeInTheDocument()
  })

  it('shows done label', () => {
    render(<StatusBar status="done" />)
    expect(screen.getByText(/migration complete/i)).toBeInTheDocument()
  })

  it('shows failed label', () => {
    render(<StatusBar status="failed" />)
    expect(screen.getByText(/failed/i)).toBeInTheDocument()
  })

  it('renders a dot element', () => {
    const { container } = render(<StatusBar status="done" />)
    expect(container.querySelector('.dot')).toBeInTheDocument()
  })

  it('applies correct dot class for status', () => {
    const { container } = render(<StatusBar status="translating" />)
    expect(container.querySelector('.dot-translating')).toBeInTheDocument()
  })
})
