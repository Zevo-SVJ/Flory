/**
 * Joins class names, dropping falsy values.
 *
 * Deliberately five lines rather than a `clsx` + `tailwind-merge` dependency:
 * Worth's components own their class strings, so there are no conflicting
 * utilities to merge away.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
