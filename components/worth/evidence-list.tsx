import type { Evidence } from '@/lib/analysis/types'
import { SIGNAL_LABEL } from '@/lib/analysis/verdict'
import { Card } from '@/components/ui/card'

/**
 * The evidence behind a verdict.
 *
 * Every claim carries its source. When the research engine ships, `source.url`
 * will link out; until then the fixture engine labels each one plainly as
 * fixture data rather than inventing a citation.
 */
export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  return (
    <Card className="p-5">
      <h2 className="text-graphite text-[0.6875rem] font-medium tracking-[0.14em] uppercase">
        Evidence
      </h2>
      <ul className="divide-line mt-3 flex flex-col divide-y">
        {evidence.map((item) => (
          <li key={item.id} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
            <span className="text-faint text-[0.6875rem] font-medium tracking-[0.1em] uppercase">
              {SIGNAL_LABEL[item.kind]}
            </span>
            <p className="text-ink-soft text-[0.9375rem] leading-snug">{item.claim}</p>
            {item.source.url ? (
              <a
                href={item.source.url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="text-graphite hover:text-ink inline-flex w-fit text-[0.8125rem] underline underline-offset-4"
              >
                {item.source.label}
              </a>
            ) : (
              <span className="text-faint text-[0.8125rem]">{item.source.label}</span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  )
}
