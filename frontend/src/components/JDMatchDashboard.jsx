// /**
//  * src/components/JDMatchDashboard.jsx
//  *
//  * Fixed to use the app's actual design tokens (border, surface, surface2,
//  * muted, accent) instead of stock Tailwind palette classes — the earlier
//  * version used bg-indigo-600 / text-slate-800 / emerald/rose-50 etc, which
//  * your Tailwind theme doesn't define, so those utilities compiled to
//  * nothing (plain white textarea, unstyled button, invisible gauge ring).
//  * Semantic status colors (score tone, matched/missing) now use inline
//  * style hex values so they render regardless of theme config.
//  * Also fixes the skill-pill row overflowing past the card into the ATS
//  * panel (missing flex-wrap / min-w-0), and replaces the fragile
//  * negative-margin gauge-label overlay with a proper absolute overlay.
//  */

// import { useState } from 'react'
// import { analyzeJd } from '../api/resumeApi.js'

// function scoreTone(score) {
//   if (score >= 75) return { hex: '#34d399', label: 'Strong match' }
//   if (score >= 50) return { hex: '#fbbf24', label: 'Partial match' }
//   return { hex: '#fb7185', label: 'Needs work' }
// }

// function MatchScoreGauge({ score }) {
//   const tone = scoreTone(score)
//   const radius = 46
//   const circumference = 2 * Math.PI * radius
//   const clamped = Math.min(Math.max(score, 0), 100)
//   const offset = circumference - (clamped / 100) * circumference

//   return (
//     <div className="flex shrink-0 flex-col items-center gap-2">
//       <div className="relative h-32 w-32">
//         <svg viewBox="0 0 108 108" className="h-32 w-32 -rotate-90">
//           <circle
//             cx="54"
//             cy="54"
//             r={radius}
//             strokeWidth="10"
//             fill="none"
//             style={{ stroke: 'rgba(255,255,255,0.12)' }}
//           />
//           <circle
//             cx="54"
//             cy="54"
//             r={radius}
//             strokeWidth="10"
//             fill="none"
//             strokeLinecap="round"
//             style={{
//               stroke: tone.hex,
//               strokeDasharray: circumference,
//               strokeDashoffset: offset,
//               transition: 'stroke-dashoffset 0.7s ease-out',
//             }}
//           />
//         </svg>
//         <div className="absolute inset-0 flex flex-col items-center justify-center">
//           <span className="text-2xl font-semibold" style={{ color: tone.hex }}>
//             {Math.round(clamped)}%
//           </span>
//         </div>
//       </div>
//       <span className="font-mono text-xs uppercase tracking-widest text-muted">
//         {tone.label}
//       </span>
//     </div>
//   )
// }

// function SkillPillList({ title, skills, tone }) {
//   const style =
//     tone === 'matched'
//       ? { color: '#34d399', borderColor: 'rgba(52,211,153,0.35)', backgroundColor: 'rgba(52,211,153,0.08)' }
//       : { color: '#fb7185', borderColor: 'rgba(251,113,133,0.35)', backgroundColor: 'rgba(251,113,133,0.08)' }

//   return (
//     <div className="min-w-0 flex-1">
//       <h4 className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
//         {title} ({skills.length})
//       </h4>
//       {skills.length === 0 ? (
//         <p className="text-sm text-muted">Nothing here.</p>
//       ) : (
//         <div className="flex flex-wrap gap-2">
//           {skills.map((skill) => (
//             <span
//               key={skill}
//               className="rounded-full border px-2.5 py-1 text-xs font-mono"
//               style={style}
//             >
//               {skill}
//             </span>
//           ))}
//         </div>
//       )}
//     </div>
//   )
// }

// export default function JDMatchDashboard({ resumeText, onActiveJdChange }) {
//   const [jdText, setJdText] = useState('')
//   const [result, setResult] = useState(null)
//   const [isLoading, setIsLoading] = useState(false)
//   const [error, setError] = useState(null)

//   const handleJdChange = (value) => {
//     setJdText(value)
//     onActiveJdChange?.(value)
//   }

//   const handleAnalyze = async () => {
//     if (!resumeText?.trim() || !jdText.trim()) {
//       setError('Add a job description before analyzing.')
//       return
//     }

//     setIsLoading(true)
//     setError(null)

//     try {
//       const match = await analyzeJd(resumeText, jdText)
//       setResult(match)
//     } catch (err) {
//       setError(err instanceof Error ? err.message : 'Failed to analyze match.')
//     } finally {
//       setIsLoading(false)
//     }
//   }

//   return (
//     <div className="w-full min-w-0 overflow-hidden rounded-xl border border-border bg-surface p-6">
//       <h3 className="text-lg font-semibold">Job Description &amp; Skill Gap Analysis</h3>
//       <p className="mt-1 text-sm text-muted">
//         Paste a target job description to see how your resume stacks up.
//       </p>

//       <textarea
//         value={jdText}
//         onChange={(e) => handleJdChange(e.target.value)}
//         placeholder="Paste the target job description here…"
//         rows={6}
//         className="mt-4 w-full resize-y rounded-md border border-border bg-surface2 p-3 text-sm font-mono placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
//       />

//       <div className="mt-3 flex items-center gap-3">
//         <button
//           type="button"
//           onClick={handleAnalyze}
//           disabled={isLoading}
//           className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 font-mono text-xs uppercase tracking-widest text-accent hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
//         >
//           {isLoading && (
//             <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
//           )}
//           {isLoading ? 'Analyzing…' : 'Analyze Match'}
//         </button>
//         {error && (
//           <span className="text-sm" style={{ color: '#fb7185' }}>
//             {error}
//           </span>
//         )}
//       </div>

//       {result && (
//         <div className="mt-6 flex flex-col gap-6 border-t border-border pt-6 sm:flex-row sm:flex-wrap">
//           <MatchScoreGauge score={result.match_percentage} />
//           <div className="flex min-w-0 flex-1 flex-col gap-6 sm:flex-row sm:flex-wrap">
//             <SkillPillList title="Matched Skills" skills={result.matched_skills} tone="matched" />
//             <SkillPillList title="Missing Skills" skills={result.missing_skills} tone="missing" />
//           </div>
//         </div>
//       )}
//     </div>
//   )
// }

/**
 * src/components/JDMatchDashboard.jsx
 *
 * Fixed to use the app's actual design tokens (border, surface, surface2,
 * muted, accent) instead of stock Tailwind palette classes — the earlier
 * version used bg-indigo-600 / text-slate-800 / emerald/rose-50 etc, which
 * your Tailwind theme doesn't define, so those utilities compiled to
 * nothing (plain white textarea, unstyled button, invisible gauge ring).
 * Semantic status colors (score tone, matched/missing) now use inline
 * style hex values so they render regardless of theme config.
 * Also fixes the skill-pill row overflowing past the card into the ATS
 * panel (missing flex-wrap / min-w-0), and replaces the fragile
 * negative-margin gauge-label overlay with a proper absolute overlay.
 *
 * Added: renders analysis_summary and missing_other_requirements from
 * jd_matcher.py's JDMatchResult (previously fetched but never displayed).
 */

import { useState } from 'react'
import { analyzeJd } from '../api/resumeApi.js'

function scoreTone(score) {
  if (score >= 75) return { hex: '#34d399', label: 'Strong match' }
  if (score >= 50) return { hex: '#fbbf24', label: 'Partial match' }
  return { hex: '#fb7185', label: 'Needs work' }
}

function MatchScoreGauge({ score }) {
  const tone = scoreTone(score)
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const clamped = Math.min(Math.max(score, 0), 100)
  const offset = circumference - (clamped / 100) * circumference

  return (
    <div className="flex shrink-0 flex-col items-center gap-2">
      <div className="relative h-32 w-32">
        <svg viewBox="0 0 108 108" className="h-32 w-32 -rotate-90">
          <circle
            cx="54"
            cy="54"
            r={radius}
            strokeWidth="10"
            fill="none"
            style={{ stroke: 'rgba(255,255,255,0.12)' }}
          />
          <circle
            cx="54"
            cy="54"
            r={radius}
            strokeWidth="10"
            fill="none"
            strokeLinecap="round"
            style={{
              stroke: tone.hex,
              strokeDasharray: circumference,
              strokeDashoffset: offset,
              transition: 'stroke-dashoffset 0.7s ease-out',
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold" style={{ color: tone.hex }}>
            {Math.round(clamped)}%
          </span>
        </div>
      </div>
      <span className="font-mono text-xs uppercase tracking-widest text-muted">
        {tone.label}
      </span>
    </div>
  )
}

function SkillPillList({ title, skills, tone }) {
  const style =
    tone === 'matched'
      ? { color: '#34d399', borderColor: 'rgba(52,211,153,0.35)', backgroundColor: 'rgba(52,211,153,0.08)' }
      : { color: '#fb7185', borderColor: 'rgba(251,113,133,0.35)', backgroundColor: 'rgba(251,113,133,0.08)' }

  return (
    <div className="min-w-0 flex-1">
      <h4 className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
        {title} ({skills.length})
      </h4>
      {skills.length === 0 ? (
        <p className="text-sm text-muted">Nothing here.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full border px-2.5 py-1 text-xs font-mono"
              style={style}
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function OtherRequirementsList({ requirements }) {
  if (!requirements || requirements.length === 0) return null

  return (
    <div className="mt-4 border-t border-border pt-4">
      <h4 className="mb-2 font-mono text-xs uppercase tracking-widest text-muted">
        Other Requirements to Note ({requirements.length})
      </h4>
      <div className="flex flex-wrap gap-2">
        {requirements.map((req) => (
          <span
            key={req}
            className="rounded-full border border-border px-2.5 py-1 text-xs font-mono text-muted"
          >
            {req}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function JDMatchDashboard({ resumeText, onActiveJdChange }) {
  const [jdText, setJdText] = useState('')
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleJdChange = (value) => {
    setJdText(value)
    onActiveJdChange?.(value)
  }

  const handleAnalyze = async () => {
    if (!resumeText?.trim() || !jdText.trim()) {
      setError('Add a job description before analyzing.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const match = await analyzeJd(resumeText, jdText)
      setResult(match)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze match.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full min-w-0 overflow-hidden rounded-xl border border-border bg-surface p-6">
      <h3 className="text-lg font-semibold">Job Description &amp; Skill Gap Analysis</h3>
      <p className="mt-1 text-sm text-muted">
        Paste a target job description to see how your resume stacks up.
      </p>

      <textarea
        value={jdText}
        onChange={(e) => handleJdChange(e.target.value)}
        placeholder="Paste the target job description here…"
        rows={6}
        className="mt-4 w-full resize-y rounded-md border border-border bg-surface2 p-3 text-sm font-mono placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      <div className="mt-3 flex items-center gap-3">
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 font-mono text-xs uppercase tracking-widest text-accent hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading && (
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          )}
          {isLoading ? 'Analyzing…' : 'Analyze Match'}
        </button>
        {error && (
          <span className="text-sm" style={{ color: '#fb7185' }}>
            {error}
          </span>
        )}
      </div>

      {result && (
        <div className="mt-6 border-t border-border pt-6">
          {result.analysis_summary && (
            <p className="mb-6 text-sm text-muted">{result.analysis_summary}</p>
          )}

          <div className="flex flex-col gap-6 sm:flex-row sm:flex-wrap">
            <MatchScoreGauge score={result.match_percentage} />
            <div className="flex min-w-0 flex-1 flex-col gap-6 sm:flex-row sm:flex-wrap">
              <SkillPillList title="Matched Skills" skills={result.matched_skills} tone="matched" />
              <SkillPillList title="Missing Skills" skills={result.missing_skills} tone="missing" />
            </div>
          </div>

          <OtherRequirementsList requirements={result.missing_other_requirements} />
        </div>
      )}
    </div>
  )
}
