import type { ImgHTMLAttributes } from 'react'

type BrandProps = Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'alt'> & {
  compact?: boolean
}

export function Brand({ compact = false, className = '', ...props }: BrandProps) {
  return (
    <img
      src={compact ? '/tacho-symbol.svg' : '/tacho-lockup-currentcolor.svg?v=2'}
      alt={compact ? '' : 'Tacho'}
      aria-hidden={compact || undefined}
      className={`block object-contain ${className}`}
      {...props}
    />
  )
}

export function BrandFallback({ className = '' }: { className?: string }) {
  return <img src="/tacho-symbol.svg" alt="" aria-hidden="true" className={`block object-contain ${className}`} />
}
