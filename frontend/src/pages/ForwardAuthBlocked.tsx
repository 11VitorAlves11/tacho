import { AuthLayout } from '../auth/AuthLayout'
import type { ForwardLoginBlockReason } from '../api/types'

const MESSAGES: Record<ForwardLoginBlockReason, string> = {
  no_account:
    'A tua conta ainda não foi criada nesta app. Pede a quem já tem acesso para te adicionar em Menu → Adicionar pessoa.',
  no_membership: 'A tua conta existe mas não tem acesso a este agregado. Contacta o administrador.',
  inactive: 'A tua conta foi desativada. Contacta o administrador.',
}

export function ForwardAuthBlocked({ reason, email }: { reason: ForwardLoginBlockReason; email?: string }) {
  return (
    <AuthLayout title="Tacho" subtitle="Sessão iniciada pelo proxy, mas ainda falta um passo.">
      <p className="text-sm text-text-primary">{MESSAGES[reason]}</p>
      {email && (
        <p className="mt-3 text-xs text-text-secondary">
          Autenticado como <span className="font-medium">{email}</span>.
        </p>
      )}
    </AuthLayout>
  )
}
