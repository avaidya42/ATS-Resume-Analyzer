const LABELS = {
  structure: 'Structure',
  formatting: 'Formatting',
  section_completeness: 'Section Completeness',
  keyword_density: 'Keyword Density',
  technical_skills: 'Technical Skills',
  action_verbs: 'Action Verbs',
  quantified_achievements: 'Quantified Achievements',
  readability: 'Readability',
}

function scoreColor(score) {
  if (score >= 75) return 'text-accent'
  if (score >= 50) return 'text-accent2'
  return 'text-red-400'
}

function ringColor(score) {
  if (score >= 75) return '#4FD1C5'
  if (score >= 50) return '#F2A65A'
  return '#F87171'
}

export default function ATSScore({ ats = {} }) {
  // Safe default values so it never crashes if ats or notes are missing/undefined
  const overall_score = ats?.overall_score ?? 0
  const breakdown = ats?.breakdown ?? {}
  const notes = ats?.notes ?? []

  const circumference = 2 * Math.PI * 54
  const offset = circumference - (overall_score / 100) * circumference

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <h3 className="font-mono text-xs uppercase tracking-widest text-muted">ATS Score</h3>

      <div className="mt-4 flex items-center gap-6">
        <svg width="120" height="120" className="shrink-0">
          <circle cx="60" cy="60" r="54" fill="none" stroke="#232C3A" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="54" fill="none"
            stroke={ringColor(overall_score)}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 60 60)"
          />
          <text x="60" y="66" textAnchor="middle" className="font-mono" fontSize="24" fill="#E2E8F0">
            {overall_score}
          </text>
        </svg>

        {notes.length > 0 && (
          <ul className="flex-1 space-y-1 text-sm">
            {notes.map((note, i) => (
              <li key={i} className="text-muted">— {note}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-6 space-y-3">
        {Object.entries(breakdown).map(([key, value]) => (
          <div key={key}>
            <div className="flex justify-between font-mono text-xs">
              <span className="text-muted">{LABELS[key] ?? key}</span>
              <span className={scoreColor(value)}>{value}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-surface2">
              <div
                className="h-1.5 rounded-full bg-accent"
                style={{ width: `${value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
