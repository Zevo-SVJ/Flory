import { test, expect } from '@playwright/test'

/**
 * Every width Worth is expected to work at. 390 is the primary reference
 * (iPhone 13/14/15/16); 320 is the smallest supported.
 */
const WIDTHS = [320, 375, 390, 430, 768, 1024, 1280]

/** Routes reachable without a Supabase session. */
const PUBLIC_ROUTES = ['/', '/pricing', '/login', '/signup', '/forgot-password']

for (const path of PUBLIC_ROUTES) {
  for (const width of WIDTHS) {
    test(`${path} has no horizontal overflow at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto(path, { waitUntil: 'load' })

      const { scrollWidth, clientWidth } = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }))

      expect(
        scrollWidth,
        `${path} scrolls sideways at ${width}px (${scrollWidth} > ${clientWidth})`,
      ).toBeLessThanOrEqual(clientWidth)
    })
  }
}

/**
 * The landing page runs several timed sequences, and a transform that pushes a
 * column past the viewport is an overflow for as long as it runs even when a
 * parent clips it. So the landing page is measured *while* it animates, after
 * it settles, and at every scroll depth — and both the documentElement and the
 * body are checked, since a stray element can widen either one.
 */
for (const width of WIDTHS) {
  test(`the landing page never moves sideways at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/', { waitUntil: 'domcontentloaded' })

    const measure = () =>
      page.evaluate(() => ({
        doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        body: document.body.scrollWidth - document.body.clientWidth,
      }))

    const samples: { at: string; doc: number; body: number }[] = []

    // While the hero sequence is running, and once it has settled.
    for (const at of [250, 900, 1700, 2800]) {
      await page.waitForTimeout(at === 250 ? 250 : 650)
      samples.push({ at: `hero+${at}ms`, ...(await measure()) })
    }

    // And at every screen down the page, where the scroll-triggered scenes run.
    const height = await page.evaluate(() => document.body.scrollHeight)
    for (let y = 0; y < height; y += 700) {
      await page.evaluate((v) => window.scrollTo(0, v), y)
      await page.waitForTimeout(120)
      samples.push({ at: `y=${y}`, ...(await measure()) })
    }

    const worst = samples.reduce(
      (acc, s) => (Math.max(s.doc, s.body) > Math.max(acc.doc, acc.body) ? s : acc),
      samples[0]!,
    )

    expect(
      Math.max(worst.doc, worst.body),
      `landing page scrolls sideways at ${width}px (${worst.at}: doc +${worst.doc}, body +${worst.body})`,
    ).toBeLessThanOrEqual(0)
  })
}

test('interactive targets on the landing page clear 44px', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/', { waitUntil: 'load' })

  const undersized = await page.evaluate(() => {
    const problems: string[] = []
    const nodes = document.querySelectorAll('a, button, input, [role="button"]')
    for (const node of nodes) {
      const el = node as HTMLElement
      const rect = el.getBoundingClientRect()
      // Skip anything not rendered (the sticky bar starts translated away).
      if (rect.width === 0 || rect.height === 0) continue
      if (el.closest('[aria-hidden="true"]')) continue
      // WCAG 2.5.8 exempts targets whose size is constrained by the
      // line-height of the sentence they sit in. Forcing a 44px box onto a
      // link inside running text would wreck the paragraph, so inline links
      // are checked for presence, not height.
      if (el.tagName === 'A' && el.closest('p') && getComputedStyle(el).display === 'inline') {
        continue
      }
      if (rect.height < 44) {
        problems.push(
          `${el.tagName} "${(el.textContent ?? '').trim().slice(0, 30)}" h=${Math.round(rect.height)}`,
        )
      }
    }
    return problems
  })

  expect(undersized, `Undersized touch targets: ${undersized.join(' | ')}`).toHaveLength(0)
})

test('the hero input and Analyze are both above the fold on iPhone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/', { waitUntil: 'load' })

  const input = page.getByPlaceholder('Paste a product, offer or URL…').first()
  const analyze = page.getByRole('button', { name: 'Analyze' }).first()

  for (const [name, locator] of [
    ['input', input],
    ['Analyze button', analyze],
  ] as const) {
    const box = await locator.boundingBox()
    expect(box, `${name} not found`).not.toBeNull()
    expect(box!.y + box!.height, `${name} falls below the fold`).toBeLessThanOrEqual(844)
  }
})

test('every example is labelled, never presented as real data', async ({ page }) => {
  await page.goto('/', { waitUntil: 'load' })

  // The hero, the category strip, the evidence wall, the verdict moment and
  // the money moment each carry their own disclosure. If a section is added
  // without one, this count drops.
  const disclosures = page.getByText(/illustrative/i)
  expect(await disclosures.count()).toBeGreaterThanOrEqual(4)
  await expect(disclosures.first()).toBeVisible()

  // The money section makes the strongest-sounding claim on the page, so it
  // carries an explicit denial rather than relying on the generic label.
  await expect(page.getByText(/no real users yet and makes no claim about savings/i)).toBeVisible()
})

test('a single h1 per public page', async ({ page }) => {
  for (const path of PUBLIC_ROUTES) {
    await page.goto(path, { waitUntil: 'load' })
    expect(await page.locator('h1').count(), `${path} h1 count`).toBe(1)
  }
})
