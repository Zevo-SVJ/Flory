'use client'

import { useEffect, useState } from 'react'

/**
 * Mobile sticky action.
 *
 * Appears once the hero field scrolls out of reach so Worth's one action stays
 * within thumb reach on a phone. It returns to that same field rather than
 * being a second destination, so it never competes as a CTA.
 */
export function StickyAnalyzeBar() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const target = document.getElementById('analyze')
    if (!target) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry) setVisible(!entry.isIntersecting && entry.boundingClientRect.top < 0)
      },
      { threshold: 0 },
    )

    observer.observe(target)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      aria-hidden={!visible}
      className={`pb-safe border-line bg-paper/95 fixed inset-x-0 bottom-0 z-40 border-t backdrop-blur-md transition-transform duration-300 motion-reduce:transition-none lg:hidden ${
        visible ? 'translate-y-0' : 'translate-y-full'
      }`}
    >
      <div className="px-4 py-3">
        <a
          href="#analyze"
          tabIndex={visible ? undefined : -1}
          className="bg-violet flex h-12 w-full items-center justify-center rounded-full text-base font-medium text-white"
        >
          Check something you’re buying
        </a>
      </div>
    </div>
  )
}
