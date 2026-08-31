import { SIGNAL_ORDER, SIGNAL_LABEL } from '@/lib/analysis/verdict'
import { Card } from '@/components/ui/card'

/**
 * The in-progress state.
 *
 * Shown while an analysis is queued or running. The dimensions listed are the
 * real ones the engine will work through, so the shape of this screen does not
 * change when real research replaces the fixture engine.
 */
export function AnalysisProgress() {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-page text-ink font-serif font-medium">Worth is looking into it.</h1>
        <p className="text-lead text-graphite mt-2">This usually takes a moment.</p>
      </div>

      <Card className="p-5">
        <ul className="flex flex-col gap-3">
          {SIGNAL_ORDER.map((kind, index) => (
            <li key={kind} className="flex items-center gap-3">
              <span
                className="border-line-strong bg-paper-2 size-4 shrink-0 animate-pulse rounded-full border"
                style={{ animationDelay: `${index * 140}ms` }}
                aria-hidden
              />
              <span className="text-graphite text-[0.9375rem]">{SIGNAL_LABEL[kind]}</span>
            </li>
          ))}
        </ul>
      </Card>

      {/* No auto-refresh yet: the fixture engine completes synchronously, so a
          page in this state means something stalled. */}
      <p className="text-graphite text-[0.875rem]">
        Still here after a few seconds?{' '}
        <a href="" className="text-ink font-medium underline underline-offset-4">
          Reload
        </a>
        .
      </p>
    </div>
  )
}
