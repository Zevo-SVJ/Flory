'use client'

import { useScrollProgress } from '@/lib/hooks/use-scroll-progress'
import { cn } from '@/lib/utils/cn'

/**
 * Scene 05 — value against risk.
 *
 * Worth's actual promise is not "is this good" — it is "is this worth the
 * money". Those are different questions, and the difference is a relationship
 * between three quantities, so it is drawn as one: what it costs, what you get,
 * and what could go wrong.
 *
 * The beam settles as the scene scrolls through: it starts level and comes to
 * rest tipped toward risk, which is the reading this example actually produces.
 * It is a diagram of a judgement, not a chart of data — there is nothing here
 * to read off an axis.
 *
 * Illustrative. Worth's engine isn't connected, so this reading is authored.
 */

const AXES = [
  {
    key: 'price',
    label: 'What it costs',
    value: '€1,007',
    note: 'once the fees are counted',
    tone: 'text-white',
  },
  {
    key: 'value',
    label: 'What you get',
    value: 'Solid',
    note: '4.5, support consistently praised',
    tone: 'text-buy-lift',
  },
  {
    key: 'risk',
    label: 'What could go wrong',
    value: 'Locked in',
    note: 'no refund after 14 days',
    tone: 'text-skip-lift',
  },
] as const

export function ValueRisk() {
  const ref = useScrollProgress<HTMLElement>({ pad: 0.1 })

  return (
    <section
      ref={ref}
      className="stage stage-lit stage-grid scene-in scene-out depth relative overflow-hidden py-24 sm:py-32"
    >
      <div className="relative z-[1] mx-auto max-w-6xl px-5 sm:px-6">
        <div>
          <p className="label text-electric">05 · Value against risk</p>
          {/* `ch` resolves against the element's own font size, so this has to
              sit on the heading, not on a wrapper in body type. */}
          <p className="text-statement mt-6 max-w-[16ch] font-serif font-medium text-balance text-white">
            Good isn’t the same as worth it.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 items-center gap-14 sm:mt-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)] lg:gap-20">
          {/* The instrument. A beam that comes to rest off level. */}
          <div className="relative mx-auto w-full max-w-[26rem]">
            <div className="halo relative aspect-square">
              {/* The ring it swings inside. */}
              <div className="absolute inset-[8%] rounded-full border border-white/8" />
              <div className="absolute inset-[22%] rounded-full border border-white/5" />

              {/* The beam. Rotation is driven by scroll and clamped, so it can
                  only ever settle — it never spins. */}
              <div
                className="absolute inset-0 flex items-center justify-center"
                style={{ transform: 'rotate(calc(var(--p, 1) * 11deg - 5.5deg))' }}
              >
                <div className="from-buy-lift via-electric to-skip-lift h-px w-[78%] bg-gradient-to-r" />
              </div>

              {/* The two ends of the judgement. */}
              <Pan side="left" label="Value" value="Solid" tone="text-buy-lift" />
              <Pan side="right" label="Risk" value="Locked in" tone="text-skip-lift" />

              {/* The price, at the pivot: everything is weighed against it. */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="glass glass-rim flex size-[7.5rem] flex-col items-center justify-center rounded-full sm:size-[8.5rem]">
                  <span className="label text-white/35">Costs</span>
                  <span className="tnum mt-1.5 text-[1.375rem] leading-none font-semibold tracking-[-0.03em] text-white sm:text-[1.5rem]">
                    €1,007
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* The reading, in words. */}
          <div>
            <dl className="flex flex-col">
              {AXES.map((a) => (
                <div key={a.key} className="border-t border-white/10 py-6">
                  <dt className="label text-white/35">{a.label}</dt>
                  <dd
                    className={cn(
                      'mt-2.5 text-[1.75rem] leading-none font-semibold tracking-[-0.025em] sm:text-[2rem]',
                      a.tone,
                    )}
                  >
                    {a.value}
                  </dd>
                  <dd className="mt-2 text-[0.9375rem] text-white/45">{a.note}</dd>
                </div>
              ))}
            </dl>

            <p className="text-lead mt-8 max-w-[38ch] text-white/60">
              A fine service at a price that isn’t fine, on terms you can’t leave. That is a
              different answer from “it’s good”.
            </p>
          </div>
        </div>

        <p className="mt-14 text-[0.75rem] text-white/25">
          Illustrative reading — not a real evaluation of a real seller.
        </p>
      </div>
    </section>
  )
}

function Pan({
  side,
  label,
  value,
  tone,
}: {
  side: 'left' | 'right'
  label: string
  value: string
  tone: string
}) {
  return (
    <div
      className={cn(
        'absolute top-1/2 -translate-y-1/2',
        side === 'left' ? 'left-0' : 'right-0',
        /* Each pan rides the beam: one drops as the other lifts. */
        side === 'left'
          ? 'translate-y-[calc(-50%-var(--p,1)*10px)]'
          : 'translate-y-[calc(-50%+var(--p,1)*10px)]',
        'motion-reduce:translate-y-[-50%]',
      )}
    >
      <div className="glass rounded-object px-3.5 py-3 sm:px-4">
        <p className="label text-white/35">{label}</p>
        <p className={cn('mt-1.5 text-[0.9375rem] leading-none font-semibold', tone)}>{value}</p>
      </div>
    </div>
  )
}
