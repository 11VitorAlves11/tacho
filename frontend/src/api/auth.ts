import axios from 'axios'
import { api } from './client'
import type { CurrentUser, ForwardLoginResult, OIDCStatus, SetupStatus, WorkspaceMember } from './types'

export async function getSetupStatus() {
  const { data } = await api.get<SetupStatus>('/setup/status')
  return data
}

export async function setup(name: string, email: string, password: string) {
  const { data } = await api.post<SetupStatus>('/setup', { name, email, password })
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
  await api.post('/auth/logout')
}

export async function getOIDCStatus() {
  const { data } = await api.get<OIDCStatus>('/auth/oidc/status')
  return data
}

export function oidcStartUrl(next = '/') {
  const base = api.defaults.baseURL ?? ''
  return `${base}/auth/oidc/start?next=${encodeURIComponent(next)}`
}

export async function getCurrentUser() {
  const { data } = await api.get<CurrentUser>('/users/me')
  return data
}

// Best-effort — em produção, atrás de um proxy forward-auth, inicia
// sessão automaticamente sem mostrar a página de login (ver
// `backend/app/routers/auth.py::forward_login`). Em dev, ou se desligado no
// backend, ou se o pedido não vier via proxy confiável, devolve
// `not_applicable` e cai-se de volta no login normal por password. Quando o
// O proxy já identificou a pessoa mas falta ação do administrador do lado do
// Tacho (`no_account`/`inactive`/`no_membership`), devolve `blocked` — o
// `AuthContext` usa isso para mostrar uma página de erro em vez do login.
export async function tryForwardLogin(): Promise<ForwardLoginResult> {
  try {
    await api.post('/auth/forward-login')
    return { status: 'ok' }
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const detail = err.response?.data?.detail
      if (detail && typeof detail === 'object' && ['no_account', 'inactive', 'no_membership'].includes(detail.reason)) {
        return { status: 'blocked', reason: detail.reason, email: detail.email }
      }
    }
    return { status: 'not_applicable' }
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
