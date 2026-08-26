// Frações comuns de cozinha como glifo unicode em vez de decimal — "½
// chávena" em vez de "0.5 chávena". Tolerância cobre o
// arredondamento próprio do parser de importação (backend/app/tasks.py::
// _parse_quantity arredonda a 2 casas: 1/3 vira 0.33, não 0.333…) e o erro
// de vírgula flutuante ao escalar porções.
const FRACTION_GLYPHS: [number, string][] = [
  [0.125, '⅛'],
  [0.25, '¼'],
  [1 / 3, '⅓'],
  [0.375, '⅜'],
  [0.5, '½'],
  [0.625, '⅝'],
  [2 / 3, '⅔'],
  [0.75, '¾'],
  [0.875, '⅞'],
]

export function formatQuantity(quantity: number): string {
  const rounded = Math.round(quantity * 1000) / 1000
  const whole = Math.floor(rounded)
  const fraction = rounded - whole
  const match = FRACTION_GLYPHS.find(([value]) => Math.abs(fraction - value) < 0.02)
  if (match) {
    const [, glyph] = match
    return whole > 0 ? `${whole} ${glyph}` : glyph
  }
  return (Math.round(quantity * 100) / 100).toFixed(2).replace(/\.?0+$/, '')
}

// Recalcula a quantidade para o número de porções escolhido, sem persistir
// nothing — scaling is a client-side presentation feature.
export function scaleQuantity(quantity: number, originalServings: number, desiredServings: number): number {
  return quantity * (desiredServings / originalServings)
}
