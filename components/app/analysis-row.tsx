import Link from 'next/link'
import type { Analysis } from '@/lib/analysis/types'
import { VERDICT_LABEL, VERDICT_STYLE } from '@/lib/analysis/verdict'
import { formatDate, formatMoney, displayUrl } from '@/lib/analysis/format'
import { cn } from '@/lib/utils/cn'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Queued',
  processing: 'Analysing',
  failed: 'Failed',
}

/** One row in the history and dashboard lists. */
export function AnalysisRow({ analysis }: { analysis: Analysis }) {
  const { verdict, score, status } = analysis
  const complete = status === 'complete' && verdict !== null && score !== null
  const price = formatMoney(analysis.priceMinor, analysis.currency)

  return (
    <li>
      <Link
        href={`/analyze/${analysis.id}`}
        className="rounded-object border-line bg-surface hover:border-line-strong flex items-center gap-3.5 border px-4 py-3.5 transition motion-reduce:transition-none"
      >
        {complete ? (
          <span
            className={cn(
              'tnum flex size-11 shrink-0 items-center justify-center rounded-full border text-[0.9375rem] font-semibold',
              VERDICT_STYLE[verdict].bg,
              VERDICT_STYLE[verdict].border,
              VERDICT_STYLE[verdict].text,
            )}
          >
            {score}
          </span>
        ) : (
          <span className="border-line bg-ivory-deep text-graphite flex size-11 shrink-0 items-center justify-center rounded-full border text-[0.6875rem]">
            —
          </span>
        )}

        <div className="min-w-0 flex-1">
          <p className="text-ink truncate text-[0.9375rem] font-medium">
            {analysis.title ??
              (analysis.inputUrl ? displayUrl(analysis.inputUrl, 40) : 'Screenshot')}
          </p>
          <p className="text-graphite truncate text-[0.8125rem]">
            {complete ? VERDICT_LABEL[verdict] : (STATUS_LABEL[status] ?? status)}
            {price && ` · ${price}`}
            {' · '}
            {formatDate(analysis.createdAt)}
          </p>
        </div>
      </Link>
    </li>
  )
}
