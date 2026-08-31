'use client'

import { useState } from 'react'
import { saveOnboarding, SPEND_CATEGORIES, BUYING_PRIORITIES } from '@/lib/auth/onboarding-actions'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils/cn'

/**
 * Onboarding.
 *
 * Two questions, both optional, both multi-select, and skipping is as easy as
 * answering. It exists to personalise Worth, not to qualify a lead — so it
 * never blocks someone from analysing something.
 */
export function OnboardingForm({
  next,
  initialCategories,
  initialPriorities,
}: {
  next: string
  initialCategories: string[]
  initialPriorities: string[]
}) {
  const [categories, setCategories] = useState<string[]>(initialCategories)
  const [priorities, setPriorities] = useState<string[]>(initialPriorities)

  return (
    <form action={saveOnboarding} className="flex flex-col gap-8">
      <input type="hidden" name="next" value={next} />

      <div>
        <h1 className="text-page text-ink font-serif font-medium">Two quick questions.</h1>
        <p className="text-lead text-graphite mt-2">
          They help Worth weigh what matters to you. Skip them if you’d rather not.
        </p>
      </div>

      <ChipGroup
        legend="What do you usually spend money on?"
        name="spend_categories"
        options={SPEND_CATEGORIES}
        selected={categories}
        onToggle={setCategories}
      />

      <ChipGroup
        legend="What matters most when you buy?"
        name="buying_priorities"
        options={BUYING_PRIORITIES}
        selected={priorities}
        onToggle={setPriorities}
      />

      <div className="flex flex-col gap-3 sm:flex-row-reverse sm:justify-start">
        <Button type="submit" size="lg" className="sm:px-10">
          Save and continue
        </Button>
        {/* Skip is the same action with nothing selected — one code path. */}
        <Button
          type="submit"
          variant="ghost"
          size="lg"
          name="skip"
          value="1"
          onClick={() => {
            setCategories([])
            setPriorities([])
          }}
        >
          Skip for now
        </Button>
      </div>
    </form>
  )
}

function ChipGroup({
  legend,
  name,
  options,
  selected,
  onToggle,
}: {
  legend: string
  name: string
  options: readonly string[]
  selected: string[]
  onToggle: (next: string[]) => void
}) {
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-ink text-[1.0625rem] font-medium">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => {
          const active = selected.includes(option)
          return (
            <button
              key={option}
              type="button"
              aria-pressed={active}
              onClick={() =>
                onToggle(active ? selected.filter((v) => v !== option) : [...selected, option])
              }
              className={cn(
                'rounded-note min-h-11 border px-4 text-[0.9375rem] transition motion-reduce:transition-none',
                active
                  ? 'border-violet bg-violet text-white'
                  : 'border-line-strong bg-surface text-ink-soft hover:border-violet hover:text-violet-deep',
              )}
            >
              {option}
            </button>
          )
        })}
      </div>
      {selected.map((value) => (
        <input key={value} type="hidden" name={name} value={value} />
      ))}
    </fieldset>
  )
}
