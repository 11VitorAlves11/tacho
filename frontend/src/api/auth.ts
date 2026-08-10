import { api } from './client'
import type { CurrentUser, SetupStatus, WorkspaceMember } from './types'

export async function getSetupStatus() {
  const { data } = await api.get<SetupStatus>('/setup/status')
  return data
}

export async function setup(email: string, password: string) {
  const { data } = await api.post<SetupStatus>('/setup', { email, password })
  return data
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams()
  body.set('username', email)
  body.set('password', password)
  await api.post('/auth/cookie/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export async function logout() {
  await api.post('/auth/cookie/logout')
}

export async function getCurrentUser() {
  const { data } = await api.get<CurrentUser>('/users/me')
  return data
}

// Best-effort — em produção, atrás do forward-auth do Authentik, inicia
// sessão automaticamente sem mostrar a página de login (ver
// `backend/app/routers/auth.py::forward_login`). Em dev, ou se desligado no
// backend, dá sempre 404 e cai-se de volta no login normal por password.
export async function tryForwardLogin() {
  try {
    await api.post('/auth/forward-login')
    return true
  } catch {
    return false
  }
}

export async function listWorkspaceMembers() {
  const { data } = await api.get<WorkspaceMember[]>('/workspace/members')
  return data
}

export async function addWorkspaceMember(email: string, password: string) {
  const { data } = await api.post<WorkspaceMember>('/workspace/members', { email, password })
  return data
}

export async function removeWorkspaceMember(id: string) {
  await api.delete(`/workspace/members/${id}`)
}

export async function updatePassword(password: string) {
  await api.patch('/users/me', { password })
}

export async function updateEmail(email: string) {
  await api.patch('/users/me', { email })
}

export async function updateName(name: string) {
  await api.patch('/users/me', { name })
}
