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

export async function listWorkspaceMembers() {
  const { data } = await api.get<WorkspaceMember[]>('/workspace/members')
  return data
}

export async function addWorkspaceMember(email: string, password: string) {
  const { data } = await api.post<WorkspaceMember>('/workspace/members', { email, password })
  return data
}
