'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils/cn'

const ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { href: '/analyze', label: 'Analyze', icon: SearchIcon },
  { href: '/history', label: 'History', icon: ClockIcon },
  { href: '/settings', label: 'Settings', icon: GearIcon },
] as const

function useActive(href: string) {
  const pathname = usePathname()
  return pathname === href || pathname.startsWith(`${href}/`)
}

/**
 * Bottom tab bar on phones — thumb-reachable and natively familiar, clearing
 * the iPhone home indicator via the safe-area inset.
 */
export function MobileTabBar() {
  return (
    <nav
      aria-label="Main"
      className="pb-safe border-line bg-paper/95 fixed inset-x-0 bottom-0 z-40 border-t backdrop-blur-md lg:hidden"
    >
      <ul className="flex">
        {ITEMS.map((item) => (
          <TabItem key={item.href} {...item} />
        ))}
      </ul>
    </nav>
  )
}

function TabItem({
  href,
  label,
  icon: Icon,
}: {
  href: string
  label: string
  icon: () => React.ReactElement
}) {
  const active = useActive(href)
  return (
    <li className="flex-1">
      <Link
        href={href}
        aria-current={active ? 'page' : undefined}
        className={cn(
          'flex min-h-14 flex-col items-center justify-center gap-1 px-1 py-2 text-[0.6875rem] font-medium transition',
          'motion-reduce:transition-none',
          active ? 'text-violet' : 'text-faint',
        )}
      >
        <Icon />
        {label}
      </Link>
    </li>
  )
}

/** Sidebar from large screens up. */
export function DesktopSidebar() {
  return (
    <nav aria-label="Main" className="flex flex-col gap-1">
      {ITEMS.map((item) => (
        <SidebarItem key={item.href} {...item} />
      ))}
    </nav>
  )
}

function SidebarItem({
  href,
  label,
  icon: Icon,
}: {
  href: string
  label: string
  icon: () => React.ReactElement
}) {
  const active = useActive(href)
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'rounded-input flex min-h-11 items-center gap-2.5 px-3 text-[0.9375rem] transition',
        'motion-reduce:transition-none',
        active
          ? 'bg-paper-2 text-ink font-medium'
          : 'text-graphite hover:bg-paper-2 hover:text-ink',
      )}
    >
      <Icon />
      {label}
    </Link>
  )
}

/* Four inline icons instead of an icon package. */
const S = {
  width: 17,
  height: 17,
  viewBox: '0 0 18 18',
  fill: 'none',
  'aria-hidden': true,
} as const
const P = {
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
} as const

function HomeIcon() {
  return (
    <svg {...S}>
      <path d="M2.5 7.2 9 2.2l6.5 5v7.3a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1V7.2Z" {...P} />
    </svg>
  )
}
function SearchIcon() {
  return (
    <svg {...S}>
      <circle cx="8" cy="8" r="5.2" {...P} />
      <path d="m12 12 3.3 3.3" {...P} />
    </svg>
  )
}
function ClockIcon() {
  return (
    <svg {...S}>
      <circle cx="9" cy="9" r="6.5" {...P} />
      <path d="M9 5.3V9l2.6 1.6" {...P} />
    </svg>
  )
}
function GearIcon() {
  return (
    <svg {...S}>
      <circle cx="9" cy="9" r="2.4" {...P} />
      <path
        d="M14.3 11a1.2 1.2 0 0 0 .24 1.32l.04.05a1.45 1.45 0 1 1-2.05 2.05l-.05-.04a1.2 1.2 0 0 0-1.32-.24 1.2 1.2 0 0 0-.73 1.1v.13a1.45 1.45 0 1 1-2.9 0v-.07a1.2 1.2 0 0 0-.79-1.1 1.2 1.2 0 0 0-1.32.24l-.05.04A1.45 1.45 0 1 1 3.32 12.4l.04-.05a1.2 1.2 0 0 0 .24-1.32 1.2 1.2 0 0 0-1.1-.73H2.4a1.45 1.45 0 1 1 0-2.9h.07a1.2 1.2 0 0 0 1.1-.79 1.2 1.2 0 0 0-.24-1.32l-.04-.05A1.45 1.45 0 1 1 5.34 3.3l.05.04a1.2 1.2 0 0 0 1.32.24h.06a1.2 1.2 0 0 0 .73-1.1V2.4a1.45 1.45 0 1 1 2.9 0v.07a1.2 1.2 0 0 0 .73 1.1 1.2 1.2 0 0 0 1.32-.24l.05-.04a1.45 1.45 0 1 1 2.05 2.05l-.04.05a1.2 1.2 0 0 0-.24 1.32v.06a1.2 1.2 0 0 0 1.1.73h.13a1.45 1.45 0 1 1 0 2.9h-.07a1.2 1.2 0 0 0-1.1.73Z"
        {...P}
      />
    </svg>
  )
}
