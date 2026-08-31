/**
 * Input validation for everything a user can submit to Worth.
 *
 * This runs on the server before anything is persisted or handed to the
 * analysis engine. It is the boundary where untrusted input stops being
 * untrusted.
 */

import type { Category } from './types'

const ALLOWED_PROTOCOLS = new Set(['http:', 'https:'])

export const CATEGORIES: Category[] = ['product', 'software', 'course', 'other']

export const CATEGORY_LABEL: Record<Category, string> = {
  product: 'Product',
  software: 'Software',
  course: 'Course',
  other: 'Other',
}

export function isCategory(value: unknown): value is Category {
  return typeof value === 'string' && (CATEGORIES as string[]).includes(value)
}

export type UrlValidation = { ok: true; url: string } | { ok: false; error: string }

/**
 * Normalises and validates a submitted URL.
 *
 * Accepts a bare host ("amazon.de/dp/X") by assuming https. Rejects anything
 * that is not http(s) — `javascript:`, `data:` and `file:` are all refused
 * rather than stored and later rendered as a link.
 */
export function validateUrl(raw: string): UrlValidation {
  const trimmed = raw.trim()

  if (!trimmed) {
    return { ok: false, error: 'Paste a link to something you are thinking about buying.' }
  }

  if (trimmed.length > 2048) {
    return { ok: false, error: 'That link is too long. Try the product page link instead.' }
  }

  const candidate = /^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

  let parsed: URL
  try {
    parsed = new URL(candidate)
  } catch {
    return { ok: false, error: "That doesn't look like a link. Check it and try again." }
  }

  if (!ALLOWED_PROTOCOLS.has(parsed.protocol)) {
    return { ok: false, error: 'Worth can only analyse http and https links.' }
  }

  // A hostname with no dot is not a public site (localhost, intranet names).
  if (!parsed.hostname.includes('.') || parsed.hostname.endsWith('.')) {
    return { ok: false, error: 'That link points somewhere Worth cannot reach.' }
  }

  return { ok: true, url: parsed.toString() }
}

/* ------------------------------------------------------------------------ */
/* Screenshot uploads                                                        */
/* ------------------------------------------------------------------------ */

export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024

export const ACCEPTED_IMAGE_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/heic',
  'image/heif',
] as const

const EXTENSION_BY_TYPE: Record<string, string> = {
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'image/webp': 'webp',
  'image/heic': 'heic',
  'image/heif': 'heif',
}

export type UploadValidation = { ok: true; extension: string } | { ok: false; error: string }

/** Validates MIME type, size and resolves a safe extension we control. */
export function validateUpload(file: { type: string; size: number }): UploadValidation {
  if (!(ACCEPTED_IMAGE_TYPES as readonly string[]).includes(file.type)) {
    return { ok: false, error: 'Upload a PNG, JPEG, WebP or HEIC image.' }
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return { ok: false, error: 'That image is over 8 MB. Try a smaller screenshot.' }
  }
  if (file.size === 0) {
    return { ok: false, error: 'That file is empty.' }
  }
  // The extension is derived from the validated MIME type, never from the
  // user-supplied filename.
  const extension = EXTENSION_BY_TYPE[file.type]
  if (!extension) return { ok: false, error: 'Unsupported image type.' }
  return { ok: true, extension }
}
