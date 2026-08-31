/**
 * Product imagery used in the illustrative examples.
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Every image on the landing page is resolved through here, so swapping the
 * current assets for real product photography is a one-line change per entry
 * and touches no component.
 *
 * The assets shipped today are locally authored SVG product renders, not
 * photographs. This build environment's network policy blocks every image host
 * (Wikimedia, Unsplash and any CDN all return 403 at the egress gateway), so
 * no real photograph could be downloaded into the repository.
 *
 * TO USE REAL PHOTOGRAPHY
 * -----------------------
 *   1. Drop the file into `public/images/products/` (e.g. `headphones.jpg`).
 *   2. Change `src` below and set `kind: 'photo'`.
 * Nothing else needs to change — `<ProductImage>` handles both, and `photo`
 * assets get object-cover framing while `render` assets get object-contain.
 */

export interface ProductAsset {
  src: string
  alt: string
  /** 'render' = locally authored vector art. 'photo' = real photography. */
  kind: 'render' | 'photo'
  width: number
  height: number
}

export type ProductAssetKey = 'headphones' | 'course'

/* Typed as the interface rather than `as const`, so `kind` stays a union and
   a component can still branch on photo vs render after a swap. */
export const PRODUCT_ASSETS: Record<ProductAssetKey, ProductAsset> = {
  headphones: {
    src: '/images/products/headphones.svg',
    alt: 'Over-ear noise-cancelling headphones',
    kind: 'render',
    width: 440,
    height: 420,
  },
  course: {
    src: '/images/products/course.svg',
    alt: 'Online course shown on a laptop',
    kind: 'render',
    width: 420,
    height: 420,
  },
}
