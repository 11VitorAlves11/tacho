import { describe, expect, it } from 'vitest'

import { axisTicks, buildBarChart, buildLineChart, fillMonths, formatMoney, lastPriceLabel, monthKeys, monthLabel, niceCeiling, seriesValues } from './prices'

const box = { width: 200, height: 120, top: 10, right: 10, bottom: 10, left: 40 }
const point = (purchased_on: string, price: number, quantity: number | null = null, unit: string | null = null) => ({
  purchased_on,
  price,
  quantity,
  unit,
  unit_price: quantity ? price / quantity : null,
})

describe('money formatting', () => {
  it('formats euros for the current language', () => {
    expect(formatMoney(1.5, 'pt-PT').replace(/\s/g, ' ')).toBe('1,50 €')
    expect(formatMoney(1234.5, 'en')).toBe('€1,234.50')
  })

  it('shows the unit price next to the last price only when it is known', () => {
    const entry = { id: '1', pantry_item_id: 'i', price: 2.4, quantity: 2, unit: 'kg', store: null, purchased_on: '2026-01-01', source: 'manual' as const, created_at: '', unit_price: 1.2 }
    expect(lastPriceLabel(entry, 'en')).toBe('€2.40 · €1.20/kg')
    expect(lastPriceLabel({ ...entry, quantity: null, unit_price: null }, 'en')).toBe('€2.40')
  })
})

describe('month bucketing', () => {
  it('lists the months ending in the current one, across a year boundary', () => {
    expect(monthKeys(3, new Date(2026, 0, 31))).toEqual(['2025-11', '2025-12', '2026-01'])
  })

  it('fills months without purchases with zero and drops months outside the window', () => {
    const totals = [{ month: '2025-10', total: 9 }, { month: '2025-12', total: 12.5 }]
    expect(fillMonths(totals, 3, new Date(2026, 0, 15))).toEqual([
      { month: '2025-11', total: 0 },
      { month: '2025-12', total: 12.5 },
      { month: '2026-01', total: 0 },
    ])
  })

  it('labels months briefly without trailing dots', () => {
    expect(monthLabel('2026-03', 'en')).toBe('Mar')
    expect(monthLabel('2026-03', 'pt-PT')).not.toContain('.')
  })
})

describe('scales', () => {
  it('rounds the axis maximum up to a readable value', () => {
    expect(niceCeiling(0)).toBe(1)
    expect(niceCeiling(7.3)).toBe(10)
    expect(niceCeiling(1.8)).toBe(2)
    expect(niceCeiling(23)).toBe(25)
    expect(niceCeiling(0.42)).toBe(0.5)
  })

  it('divides the axis into readable steps', () => {
    expect(axisTicks(200)).toEqual([0, 50, 100, 150, 200])
    expect(axisTicks(2.5)).toEqual([0, 0.5, 1, 1.5, 2, 2.5])
    expect(axisTicks(5)).toEqual([0, 1, 2, 3, 4, 5])
    expect(axisTicks(1)).toEqual([0, 0.25, 0.5, 0.75, 1])
  })

  it('plots unit prices only when every point has one in the same unit', () => {
    expect(seriesValues([point('2026-01-01', 2, 2, 'kg'), point('2026-02-01', 3, 2, 'kg')])).toEqual({ mode: 'unit', unit: 'kg', values: [1, 1.5] })
    expect(seriesValues([point('2026-01-01', 2, 2, 'kg'), point('2026-02-01', 3)]).mode).toBe('total')
    expect(seriesValues([point('2026-01-01', 2, 2, 'kg'), point('2026-02-01', 3, 1, 'L')]).values).toEqual([2, 3])
  })
})

describe('line chart', () => {
  it('maps dates to x by time and values to y from zero', () => {
    const chart = buildLineChart([{ date: '2026-01-01', value: 5 }, { date: '2026-01-03', value: 10 }, { date: '2026-01-11', value: 0 }], box)
    expect(chart.max).toBe(10)
    expect(chart.coords.map(({ x, y }) => [x, y])).toEqual([[40, 60], [70, 10], [190, 110]])
    expect(chart.path).toBe('M40 60 L70 10 L190 110')
    expect(chart.ticks.map((tick) => tick.value)).toEqual([0, 2.5, 5, 7.5, 10])
    expect(chart.ticks[0].y).toBe(110)
  })

  it('centres a single purchase', () => {
    const chart = buildLineChart([{ date: '2026-01-01', value: 3 }], box)
    expect(chart.coords[0].x).toBe(115)
    expect(chart.path).toBe('M115 50')
  })
})

describe('bar chart', () => {
  it('gives each month an equal slot and scales heights to the axis maximum', () => {
    const chart = buildBarChart([{ month: '2026-01', total: 0 }, { month: '2026-02', total: 20 }], { ...box, width: 240 })
    expect(chart.max).toBe(20)
    expect(chart.bars[0]).toMatchObject({ height: 0, y: 110 })
    expect(chart.bars[1]).toMatchObject({ height: 100, y: 10 })
    expect(chart.bars[1].x).toBeGreaterThan(chart.bars[0].x + chart.bars[0].width)
  })

  it('caps the bar width on wide charts and keeps each bar centred in its slot', () => {
    const chart = buildBarChart([{ month: '2026-01', total: 5 }, { month: '2026-02', total: 10 }], { ...box, width: 1040 }, 40)
    expect(chart.bars.map((bar) => bar.width)).toEqual([40, 40])
    expect(chart.bars.map((bar) => bar.x)).toEqual([267.5, 762.5])
  })
})
