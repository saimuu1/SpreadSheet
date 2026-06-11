import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function authHeaders() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function handle(res) {
  if (res.status === 204) return null
  let body = null
  try {
    body = await res.json()
  } catch {
    /* no body */
  }
  if (!res.ok) {
    const detail = body?.detail || res.statusText || 'Request failed'
    throw new ApiError(typeof detail === 'string' ? detail : JSON.stringify(detail), res.status)
  }
  return body
}

export async function apiGet(path) {
  const res = await fetch(`${API_URL}${path}`, { headers: { ...(await authHeaders()) } })
  return handle(res)
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return handle(res)
}

export async function apiUpload(path, file, fields = {}) {
  const form = new FormData()
  form.append('file', file)
  for (const [k, v] of Object.entries(fields)) form.append(k, v)
  // Build query string for any non-file fields the endpoint expects as query params.
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { ...(await authHeaders()) },
    body: form,
  })
  return handle(res)
}

export async function apiDelete(path) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'DELETE',
    headers: { ...(await authHeaders()) },
  })
  return handle(res)
}

export { ApiError, API_URL }
