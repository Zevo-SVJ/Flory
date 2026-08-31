import { formatMoney, moneyDelta } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'

/**
 * The money row: what you're about to pay, the best price Worth found, and the
 * gap between them. The saving is the only figure that carries colour.
 */
export function MoneyRow({
  priceMinor,
  bestPriceMinor,
  currency,
  size = 'md',
  className,
}: {
  priceMinor: number | null
  bestPriceMinor: number | null
  currency: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const price = formatMoney(priceMinor, currency)
  const best = formatMoney(bestPriceMinor, currency)
  const delta = moneyDelta(priceMinor, bestPriceMinor)
  const saving = delta ? formatMoney(delta.savingMinor, currency) : null

  if (!price) return null

  const figure =
    size === 'lg' ? 'text-figure-sm' : size === 'md' ? 'text-[1.375rem] sm:text-2xl' : 'text-lg'

  return (
    <dl className={cn('grid grid-cols-3 gap-2 sm:gap-4', className)}>
      <MoneyCell label="Price" value={price} figureClass={figure} />
      {best && <MoneyCell label="Better option" value={best} figureClass={figure} />}
      {saving && (
        <MoneyCell label="Potential saving" value={saving} figureClass={figure} tone="saving" />
      )}
    </dl>
  )
}

function MoneyCell({
  label,
  value,
  figureClass,
  tone,
}: {
  label: string
  value: string
  figureClass: string
  tone?: 'saving'
}) {
  return (
    <div className="min-w-0">
      {/* Fixed label height keeps the three figures on one baseline even when
          a longer label wraps to two lines. */}
      <dt className="text-muted flex min-h-[2.3em] items-start text-[0.625rem] leading-tight font-medium tracking-[0.1em] uppercase">
        {label}
      </dt>
      <dd
        className={cn(
          'tnum mt-1 font-semibold tracking-[-0.03em]',
          figureClass,
          tone === 'saving' ? 'text-buy' : 'text-ink',
        )}
      >
        {value}
      </dd>
    </div>
  )
}
