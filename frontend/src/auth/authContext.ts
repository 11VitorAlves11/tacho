import { createContext } from 'react'
import type { CurrentUser, ForwardLoginBlockReason } from '../api/types'

interface ForwardAuthBlock {
  reason: ForwardLoginBlockReason
  email?: string
}

export interface AuthState {
  user: CurrentUser | null | undefined
  needsSetup: boolean | undefined
  forwardAuthBlocked: ForwardAuthBlock | null
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
