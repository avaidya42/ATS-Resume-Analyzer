/**
 * src/components/BulletOptimizer.jsx
 *
 * Fixed to (1) use your design tokens instead of stock indigo/rose Tailwind
 * classes that don't exist in your theme, and (2) render as an <li> — the
 * previous version rendered a <div> as a direct child of your <ul>, which
 * is invalid HTML and gets silently "corrected" by the browser, breaking
 * the list's spacing. Also removed the hover-only reveal for the rewrite
 * button since that made it unreachable on touch devices.
 */

import { useState } from 'react'
import { optimizeBullet } from '../api/resumeApi.js'

export default function OptimizableBullet({ bullet, targetJd = '', onApply }) {
  const [isLoading, setIsLoading] = useState(false)
  const [optimized, setOptimized] = useState(null)
  const [error, setError] = useState(null)

  const handleOptimize = async () => {
    setIsLoading(true)
    setError(null)
    setOptimized(null)

    try {
      const result = await optimizeBullet(bullet, targetJd)
      setOptimized(result.optimized_bullet)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rewrite failed.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAccept = () => {
    if (optimized) {
      onApply(optimized)
      setOptimized(null)
    }
  }

  const handleDiscard = () => {
    setOptimized(null)
    setError(null)
  }

  return (
    <li className="-mx-2 list-none rounded-md px-2 py-1.5 hover:bg-surface2">
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 flex-1">{bullet}</p>

        <button
          type="button"
          onClick={handleOptimize}
          disabled={isLoading}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border px-2 py-1 font-mono text-xs uppercase tracking-widest text-accent transition hover:bg-surface disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent" />
              Rewriting…
            </>
          ) : (
            <>✨ AI Rewrite</>
          )}
        </button>
      </div>

      {error && (
        <p className="mt-1 text-xs" style={{ color: '#fb7185' }}>
          {error}
        </p>
      )}

      {optimized && (
        <div className="mt-2 rounded-md border border-border bg-surface2 p-3">
          <p className="font-mono text-xs uppercase tracking-widest text-muted">
            Suggested rewrite
          </p>
          <p className="mt-1 text-sm">{optimized}</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={handleAccept}
              className="rounded-md border border-border px-3 py-1 font-mono text-xs uppercase tracking-widest text-accent hover:bg-surface"
            >
              Accept &amp; Apply
            </button>
            <button
              type="button"
              onClick={handleDiscard}
              className="rounded-md border border-border px-3 py-1 font-mono text-xs uppercase tracking-widest text-muted hover:bg-surface"
            >
              Discard
            </button>
          </div>
        </div>
      )}
    </li>
  )
}
