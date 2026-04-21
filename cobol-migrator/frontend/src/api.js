import axios from 'axios'

export async function submitMigration(payload) {
  const { data } = await axios.post('/api/migrate', payload)
  return data  // { job_id, status }
}

export async function getStatus(jobId) {
  const { data } = await axios.get(`/api/status/${jobId}`)
  return data  // { job_id, status, result, error }
}
