import { render, screen } from '@testing-library/react'
import CodePanel from '../components/CodePanel'

describe('CodePanel', () => {
  it('shows COBOL label', () => {
    render(<CodePanel original="IDENTIFICATION DIVISION." translated="def main(): pass" />)
    expect(screen.getByText('COBOL')).toBeInTheDocument()
  })

  it('shows Python label', () => {
    render(<CodePanel original="IDENTIFICATION DIVISION." translated="def main(): pass" />)
    expect(screen.getByText('Python')).toBeInTheDocument()
  })

  it('renders original code', () => {
    render(<CodePanel original="IDENTIFICATION DIVISION." translated="" />)
    expect(screen.getByText('IDENTIFICATION DIVISION.')).toBeInTheDocument()
  })

  it('renders translated code', () => {
    render(<CodePanel original="" translated="def main(): pass" />)
    expect(screen.getByText('def main(): pass')).toBeInTheDocument()
  })

  it('shows placeholder when no code', () => {
    render(<CodePanel original="" translated="" />)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})
