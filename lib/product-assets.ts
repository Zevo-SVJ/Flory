/**
 * Product imagery used in the illustrative examples.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Every image on the landing page is resolved through here, so swapping the
 * current assets for real product photography is a one-line change per entry
 * and touches no component.
 *
 * PROVENANCE
 * ----------
 * `headphones.webp` is a real photograph, not a render:
 *   Source: Wikimedia Commons, "Headphones (56330).jpg"
 *   Licence: CC0 1.0 (public domain dedication) — commercial use and
 *            modification permitted, no attribution required.
 *   Processing: the original is shot on a saturated yellow seamless. The
 *            background was keyed out in HSV (hue ~47deg, saturated, bright)
 *            and replaced with the warm neutral the Worth paper surface uses,
 *            so the product sits in the palette instead of fighting it. The
 *            headphones were then recentred on a 4:3 canvas of the same
 *            neutral and resized to 480x360, WebP q78 (5.5 kB).
 *   Two crops ship: `headphones.webp` on a light studio ground for the light
 *            sections, and `headphones-dark.webp` relit for the dark scenes.
 *   Why this product: the example analysis is about unbranded over-ear
 *            noise-cancelling headphones. Attaching an invented verdict to an
 *            identifiable brand would be unfair to that brand, so the photo is
 *            deliberately one with no legible logo.
 *
 * `course.svg` is a locally authored render, used because a photograph adds
 * nothing to "an online course" — the thing being sold is the interface.
 *
 * TO SWAP AN ASSET
 * ----------------
 *   1. Drop the file into `public/images/products/`.
 *   2. Change `src` and `kind` below.
 * Nothing else changes — `photo` assets get object-cover framing, `render`
 * assets get object-contain.
 */

export interface ProductAsset {
  src: string
  alt: string
  /** 'render' = locally authored vector art. 'photo' = real photography. */
  kind: 'render' | 'photo'
  width: number
  height: number
}

export type ProductAssetKey = 'headphones' | 'headphonesDark' | 'course'

/* Typed as the interface rather than `as const`, so `kind` stays a union and
   a component can still branch on photo vs render after a swap. */
export const PRODUCT_ASSETS: Record<ProductAssetKey, ProductAsset> = {
  headphones: {
    src: '/images/products/headphones.webp',
    alt: 'Over-ear noise-cancelling headphones',
    kind: 'photo',
    width: 480,
    height: 360,
  },
  /* The same photograph relit for Worth's dark scenes: the yellow seamless
     replaced by a violet studio pool, a cool rim drawn from the product's own
     speculars, and a contact shadow beneath it. This is the hero plate. */
  headphonesDark: {
    src: '/images/products/headphones-dark.webp',
    alt: 'Over-ear noise-cancelling headphones, lit on a dark studio set',
    kind: 'photo',
    width: 720,
    height: 540,
  },
  course: {
    src: '/images/products/course.svg',
    alt: 'Online course shown on a laptop',
    kind: 'render',
    width: 420,
    height: 420,
  },
}
