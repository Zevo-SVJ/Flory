'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { cn } from '@/lib/utils/cn'

/**
 * Scroll reveal.
 *
 * ~30 lines instead of an animation library. Fires once, then disconnects.
 * The CSS in globals.css disables it entirely under prefers-reduced-motion,
 * and the element is visible by default if JavaScript never runs.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode
  delay?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      node.dataset.shown = 'true'
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry?.isIntersecting) return
        window.setTimeout(() => {
          node.dataset.shown = 'true'
        }, delay)
        observer.disconnect()
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [delay])

  return (
    <div ref={ref} className={cn('reveal', className)}>
      {children}
    </div>
  )
}
