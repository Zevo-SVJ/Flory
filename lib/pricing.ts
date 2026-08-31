/**
 * Pricing architecture.
 *
 * Worth launches with three paid plans and no permanent free tier. Prices,
 * names and limits are NOT final and are deliberately absent — advertising a
 * number we have not committed to would be a lie to every early visitor.
 *
 * This module is the single source of truth for both the landing section and
 * /pricing. Adding Stripe later means adding `stripePriceId` here and a
 * checkout route — no page needs redesigning.
 */

export interface Plan {
  /** Provisional identifier. Safe to rename before launch. */
  id: 'starter' | 'regular' | 'pro'
  name: string
  /** Who the plan is for, in one line. */
  audience: string
  /** What changes between plans. Volume is the axis, not feature gating. */
  includes: string[]
  /** Visually emphasised, but no plan is presented as "most popular" — Worth
   *  has no users yet, so it has no idea which is popular. */
  emphasis?: boolean
  // stripePriceId?: string  ← added when billing ships
}

export const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    audience: 'For the occasional bigger purchase.',
    includes: ['A small number of analyses each month', 'Full verdict, evidence and alternatives'],
  },
  {
    id: 'regular',
    name: 'Regular',
    audience: 'For people who buy things often enough to care.',
    includes: [
      'A larger monthly allowance',
      'Full verdict, evidence and alternatives',
      'Saved history and shareable results',
    ],
    emphasis: true,
  },
  {
    id: 'pro',
    name: 'Pro',
    audience: 'For heavy researchers and resellers.',
    includes: [
      'The highest monthly allowance',
      'Everything in Regular',
      'Priority access to new analysis features',
    ],
  },
]

export const PRICING_DISCLOSURE =
  'Worth will launch as a paid product with three plans and no permanent free tier. Plan names, prices and limits are provisional and will be confirmed before launch — nothing here is final, and there is nothing to buy yet.'
