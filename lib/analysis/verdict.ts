import type { SignalKind, SignalTone, Verdict } from './types'

/**
 * Score → verdict thresholds.
 *
 * Worth is a decision product, so the bands are deliberately decisive: a score
 * either clears the bar, sits in genuine doubt, or does not clear it.
 */
export const VERDICT_THRESHOLDS = { buy: 70, thinkTwice: 40 } as const

export function verdictFromScore(score: number): Verdict {
  if (score >= VERDICT_THRESHOLDS.buy) return 'buy'
  if (score >= VERDICT_THRESHOLDS.thinkTwice) return 'think_twice'
  return 'skip'
}

export const VERDICT_LABEL: Record<Verdict, string> = {
  buy: 'Buy',
  think_twice: 'Think twice',
  skip: 'Skip',
}

/**
 * Verdict styling. These are the only chromatic tokens in the product —
 * colour in Worth always means a judgement.
 */
export const VERDICT_STYLE: Record<
  Verdict,
  { text: string; bg: string; border: string; dot: string }
> = {
  buy: {
    text: 'text-buy',
    bg: 'bg-buy-wash',
    border: 'border-buy/25',
    dot: 'bg-buy',
  },
  think_twice: {
    text: 'text-think',
    bg: 'bg-think-wash',
    border: 'border-think/25',
    dot: 'bg-think',
  },
  skip: {
    text: 'text-skip',
    bg: 'bg-skip-wash',
    border: 'border-skip/25',
    dot: 'bg-skip',
  },
}

export const SIGNAL_LABEL: Record<SignalKind, string> = {
  price: 'Price',
  fees: 'Fees',
  value: 'Value',
  reviews: 'Reviews',
  trust: 'Trust',
  risk: 'Risk',
  alternative: 'Alternatives',
}

/** What each dimension answers. Used on the landing page and the result page. */
export const SIGNAL_QUESTION: Record<SignalKind, string> = {
  price: 'Is this a good price?',
  fees: 'What does it cost once everything is added?',
  value: 'What are you actually getting?',
  reviews: 'What do buyers consistently report?',
  trust: 'Who is selling it, and can they be trusted?',
  risk: 'Are there meaningful warning signs?',
  alternative: 'Is there a better option for your money?',
}

export const TONE_STYLE: Record<SignalTone, { text: string; dot: string }> = {
  positive: { text: 'text-buy', dot: 'bg-buy' },
  caution: { text: 'text-think', dot: 'bg-think' },
  negative: { text: 'text-skip', dot: 'bg-skip' },
  neutral: { text: 'text-graphite', dot: 'bg-faint' },
}

export const SIGNAL_ORDER: SignalKind[] = [
  'price',
  'fees',
  'value',
  'reviews',
  'trust',
  'risk',
  'alternative',
]
