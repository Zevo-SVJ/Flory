/**
 * Money formatting.
 *
 * Worth stores every amount as an integer number of minor units (cents) and
 * only ever converts for display. Floating-point currency is a correctness bug
 * waiting to happen, and money is the whole point of this product.
 */

export function formatMoney(
  minorUnits: number | null | undefined,
  currency = 'EUR',
  locale = 'en-IE',
): string | null {
  if (minorUnits === null || minorUnits === undefined || !Number.isFinite(minorUnits)) return null
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: minorUnits % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(minorUnits / 100)
}

/**
 * The money delta between what the user is about to pay and the best option
 * Worth found. Positive `savingMinor` means they would save by switching.
 */
export function moneyDelta(
  priceMinor: number | null,
  bestPriceMinor: number | null,
): { savingMinor: number; isOverpaying: boolean } | null {
  if (priceMinor === null || bestPriceMinor === null) return null
  const savingMinor = priceMinor - bestPriceMinor
  if (savingMinor <= 0) return null
  return { savingMinor, isOverpaying: true }
}

export function formatDate(iso: string, locale = 'en-IE'): string {
  return new Intl.DateTimeFormat(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

/** Displays a submitted URL compactly — host plus a truncated path. */
export function displayUrl(raw: string, maxLength = 44): string {
  let text = raw
  try {
    const url = new URL(raw)
    text = url.host.replace(/^www\./, '') + url.pathname.replace(/\/$/, '')
  } catch {
    /* Not a parseable URL — fall back to the raw string. */
  }
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text
}
