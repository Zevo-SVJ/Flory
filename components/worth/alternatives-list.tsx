import type { Alternative } from '@/lib/analysis/types'
import { formatMoney } from '@/lib/analysis/format'
import { Card } from '@/components/ui/card'

/** Better options for the same money, when Worth finds any. */
export function AlternativesList({ alternatives }: { alternatives: Alternative[] }) {
  return (
    <Card className="p-5">
      <h2 className="text-muted text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
        Alternatives
      </h2>
      <ul className="divide-rule mt-3 flex flex-col divide-y">
        {alternatives.map((item) => {
          const price = formatMoney(item.priceMinor, item.currency)
          return (
            <li key={item.id} className="flex items-start gap-4 py-3 first:pt-0 last:pb-0">
              <div className="min-w-0 flex-1">
                <p className="text-ink text-[0.9375rem] font-medium">{item.title}</p>
                <p className="text-muted mt-0.5 text-[0.875rem] leading-snug">{item.reason}</p>
              </div>
              {price && (
                <span className="tnum text-buy shrink-0 text-lg font-semibold">{price}</span>
              )}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
