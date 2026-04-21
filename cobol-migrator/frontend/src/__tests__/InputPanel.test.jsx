import { render, screen, fireEvent } from '@testing-library/react'
import InputPanel from '../components/InputPanel'

describe('InputPanel', () => {
  it('renders all three tabs', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    expect(screen.getByText('Paste Code')).toBeInTheDocument()
    expect(screen.getByText('File URL')).toBeInTheDocument()
    expect(screen.getByText('Repo URL')).toBeInTheDocument()
  })

  it('shows textarea on paste tab', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    expect(screen.getByPlaceholderText(/paste cobol/i)).toBeInTheDocument()
  })

  it('submit button disabled when textarea empty', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    expect(screen.getByRole('button', { name: /migrate/i })).toBeDisabled()
  })

  it('submit button enabled after typing code', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    fireEvent.change(screen.getByPlaceholderText(/paste cobol/i), { target: { value: 'IDENTIFICATION DIVISION.' } })
    expect(screen.getByRole('button', { name: /migrate/i })).not.toBeDisabled()
  })

  it('calls onSubmit with source_code', () => {
    const onSubmit = vi.fn()
    render(<InputPanel onSubmit={onSubmit} loading={false} />)
    fireEvent.change(screen.getByPlaceholderText(/paste cobol/i), { target: { value: 'IDENTIFICATION DIVISION.' } })
    fireEvent.click(screen.getByRole('button', { name: /migrate/i }))
    expect(onSubmit).toHaveBeenCalledWith({ source_code: 'IDENTIFICATION DIVISION.' })
  })

  it('switches to File URL tab', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    fireEvent.click(screen.getByText('File URL'))
    expect(screen.getByPlaceholderText(/github.com\/owner\/repo\/blob/i)).toBeInTheDocument()
  })

  it('switches to Repo URL tab', () => {
    render(<InputPanel onSubmit={() => {}} loading={false} />)
    fireEvent.click(screen.getByText('Repo URL'))
    expect(screen.getByPlaceholderText(/github.com\/owner\/repo$/i)).toBeInTheDocument()
  })

  it('calls onSubmit with repo_url', () => {
    const onSubmit = vi.fn()
    render(<InputPanel onSubmit={onSubmit} loading={false} />)
    fireEvent.click(screen.getByText('Repo URL'))
    fireEvent.change(screen.getByPlaceholderText(/github.com\/owner\/repo$/i), { target: { value: 'https://github.com/owner/repo' } })
    fireEvent.click(screen.getByRole('button', { name: /migrate/i }))
    expect(onSubmit).toHaveBeenCalledWith({ repo_url: 'https://github.com/owner/repo' })
  })

  it('shows loading text when loading', () => {
    render(<InputPanel onSubmit={() => {}} loading={true} />)
    expect(screen.getByText(/migrating/i)).toBeInTheDocument()
  })

  it('disables submit when loading', () => {
    render(<InputPanel onSubmit={() => {}} loading={true} />)
    expect(screen.getByRole('button', { name: /migrating/i })).toBeDisabled()
  })
})
