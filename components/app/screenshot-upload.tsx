'use client'

import { useEffect, useRef, useState, useTransition } from 'react'
import { createClient } from '@/lib/supabase/client'
import { submitScreenshot } from '@/lib/analysis/actions'
import { validateUpload, ACCEPTED_IMAGE_TYPES, MAX_UPLOAD_BYTES } from '@/lib/analysis/validate'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils/cn'

/**
 * Screenshot upload.
 *
 * What is real here: the picker (including iPhone camera capture), MIME and
 * size validation, and the upload itself into a PRIVATE Supabase Storage bucket
 * under the user's own folder, enforced by storage RLS.
 *
 * What is NOT built: reading the image. Worth cannot yet identify a product
 * from a screenshot, and this deliberately does not pretend otherwise — the
 * analysis is created with the same fixture engine as any other input and is
 * labelled as such on the result.
 */
export function ScreenshotUpload({
  userId,
  defaultOpen = false,
}: {
  userId: string
  defaultOpen?: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const sectionRef = useRef<HTMLDivElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [, startTransition] = useTransition()

  // Arriving from "Upload screenshot" on the landing page should land the
  // visitor on the picker, not halfway up the URL form.
  useEffect(() => {
    if (!defaultOpen) return
    sectionRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [defaultOpen])

  function handleFile(selected: File | null) {
    setError(null)
    if (!selected) return

    const check = validateUpload({ type: selected.type, size: selected.size })
    if (!check.ok) {
      setError(check.error)
      setFile(null)
      setPreview(null)
      return
    }

    setFile(selected)
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old)
      return URL.createObjectURL(selected)
    })
  }

  async function handleUpload() {
    if (!file || !userId) return
    const check = validateUpload({ type: file.type, size: file.size })
    if (!check.ok) {
      setError(check.error)
      return
    }

    setUploading(true)
    setError(null)

    try {
      const supabase = createClient()
      // Path is scoped to the user's own folder; storage RLS enforces the same
      // rule server-side. The extension comes from the validated MIME type, not
      // from the filename.
      const path = `${userId}/${crypto.randomUUID()}.${check.extension}`
      const { error: uploadError } = await supabase.storage
        .from('analysis-uploads')
        .upload(path, file, { contentType: file.type, upsert: false })

      if (uploadError) {
        setError('That upload didn’t complete. Please try again.')
        setUploading(false)
        return
      }

      startTransition(async () => {
        const result = await submitScreenshot(path)
        if (result?.error) {
          setError(result.error)
          setUploading(false)
        }
      })
    } catch {
      setError('That upload didn’t complete. Please try again.')
      setUploading(false)
    }
  }

  return (
    <div ref={sectionRef} className="flex flex-col gap-3">
      <div>
        <h2 className="text-ink text-[0.9375rem] font-semibold">Upload a screenshot</h2>
        <p className="text-muted mt-1 text-[0.875rem] leading-snug">
          For things without a link — a listing in an app, a story, a message.
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(',')}
        // On iOS this offers the camera as well as the photo library.
        capture={undefined}
        className="sr-only"
        onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
      />

      {preview ? (
        <div className="flex flex-col gap-3">
          <div className="rounded-card border-rule bg-surface flex items-center gap-3 border p-3">
            {/* Local object URL preview; next/image adds nothing for a blob. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={preview}
              alt="Screenshot preview"
              className="rounded-input border-rule size-16 shrink-0 border object-cover"
            />
            <div className="min-w-0 flex-1">
              <p className="text-ink truncate text-[0.875rem] font-medium">{file?.name}</p>
              <p className="text-muted text-[0.8125rem]">
                {file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : ''}
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setFile(null)
                if (preview) URL.revokeObjectURL(preview)
                setPreview(null)
                if (inputRef.current) inputRef.current.value = ''
              }}
              className="rounded-chip text-muted hover:text-ink min-h-11 px-2 text-[0.875rem]"
            >
              Remove
            </button>
          </div>

          <p className="rounded-input border-rule-strong bg-paper-sunk text-muted border px-3.5 py-3 text-[0.8125rem] leading-relaxed">
            <strong className="text-ink-2 font-semibold">Heads up:</strong> Worth can’t read
            screenshots yet. Your image is stored privately and the analysis will use the same
            development fixture data as every other result until the research engine ships.
          </p>

          <Button type="button" onClick={handleUpload} disabled={uploading} size="lg">
            {uploading ? 'Uploading…' : 'Upload and continue'}
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className={cn(
            'rounded-card flex min-h-24 w-full flex-col items-center justify-center gap-1.5',
            'border-rule-strong bg-surface border border-dashed px-4 py-6 transition',
            'hover:border-ink hover:bg-paper-sunk motion-reduce:transition-none',
          )}
        >
          <span className="text-ink text-[0.9375rem] font-medium">Choose an image</span>
          <span className="text-muted text-[0.8125rem]">
            PNG, JPEG, WebP or HEIC · up to {Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)} MB
          </span>
        </button>
      )}

      {error && (
        <p role="alert" className="text-skip text-[0.875rem] font-medium">
          {error}
        </p>
      )}
    </div>
  )
}
