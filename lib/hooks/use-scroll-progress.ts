'use client'

import { useEffect, useRef } from 'react'

/**
 * Scroll progress, written straight to CSS.
 *
 * Returns a ref to attach to an element. As that element passes through the
 * viewport the hook sets `--p` on it, from 0 (its top is entering at the bottom
 * of the screen) to 1 (its bottom is leaving at the top).
 *
 * WHY THIS AND NOT A MOTION LIBRARY
 * ---------------------------------
 * Nothing here goes through React. Scroll drives a custom property, CSS turns
 * that property into a `transform`, and the compositor does the rest — so a
 * scroll costs no render, no reconciliation and no style recalculation. Adding
 * a runtime animation library to a static marketing page would have cost
 * ~50 kB of JavaScript to do less.
 *
 * Reads are batched into a rAF and the layout box is measured only on resize,
 * so the scroll handler itself never touches the layout.
 *
 * Under `prefers-reduced-motion` the hook does not attach at all and `--p`
 * stays at its stylesheet default, which every consumer defines as the
 * settled, readable state.
 */
export function useScrollProgress<T extends HTMLElement>(options?: {
  /** Extra distance, in viewport heights, before and after the element. */
  pad?: number
}) {
  const ref = useRef<T>(null)
  const pad = options?.pad ?? 0

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let top = 0
    let height = 0
    let frame = 0
    let last = -1

    const measure = () => {
      const box = node.getBoundingClientRect()
      top = box.top + window.scrollY
      height = box.height
    }

    const write = () => {
      frame = 0
      const vh = window.innerHeight
      const padding = vh * pad
      const start = top - vh - padding
      const span = height + vh + padding * 2
      if (span <= 0) return

      const p = Math.min(1, Math.max(0, (window.scrollY - start) / span))
      /* Two decimals is finer than a pixel at these ranges, and avoids
         writing a new value on every single scroll event. */
      const rounded = Math.round(p * 100) / 100
      if (rounded === last) return
      last = rounded
      node.style.setProperty('--p', String(rounded))
    }

    const onScroll = () => {
      if (frame) return
      frame = requestAnimationFrame(write)
    }

    const onResize = () => {
      measure()
      last = -1
      onScroll()
    }

    measure()
    write()

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onResize)

    /* The element's own box can change without the window resizing — a font
       loading, an image decoding, a sibling animating. */
    const observer = new ResizeObserver(onResize)
    observer.observe(node)

    return () => {
      if (frame) cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onResize)
      observer.disconnect()
    }
  }, [pad])

  return ref
}
