import { useState } from 'react'
import JDMatchDashboard from './JDMatchDashboard'
import OptimizableBullet from './BulletOptimizer'

const SECTION_ICONS = {
  skills: (
    <path d="M20.59 13.41 11 3.83A2 2 0 0 0 9.59 3.24L3 3v6.59a2 2 0 0 0 .59 1.41l9.58 9.58a2 2 0 0 0 2.83 0l4.59-4.59a2 2 0 0 0 0-2.83Z" />
  ),
  experience: (
    <>
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </>
  ),
  projects: (
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2Z" />
  ),
  education: (
    <>
      <path d="M22 10 12 5 2 10l10 5 10-5Z" />
      <path d="M6 12v5c0 1.1 2.7 2 6 2s6-.9 6-2v-5" />
    </>
  ),
  certifications: (
    <>
      <circle cx="12" cy="8" r="6" />
      <path d="m9 14-1.5 7L12 19l4.5 2L15 14" />
    </>
  ),
  achievements: (
    <path d="M12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61Z" />
  ),
  languages: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20Z" />
    </>
  ),
}

function SectionIcon({ name }) {
  const path = SECTION_ICONS[name]
  if (!path) return null
  return (
    <svg
      width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      className="text-muted"
    >
      {path}
    </svg>
  )
}

function Section({ title, icon, children }) {
  return (
    <div className="border-t border-border pt-4 first:border-t-0 first:pt-0">
      <h4 className="mb-2 flex items-center gap-1.5 font-mono text-xs uppercase tracking-widest text-muted">
        <SectionIcon name={icon} />
        {title}
      </h4>
      {children}
    </div>
  )
}

function Tag({ children }) {
  return (
    <span className="mr-2 mb-2 inline-block rounded-md border border-border bg-surface2 px-2 py-1 text-xs transition-colors hover:border-accent/40">
      {children}
    </span>
  )
}

function initials(name) {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/)
  const first = parts[0]?.[0] ?? ''
  const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return (first + last).toUpperCase()
}

export default function ResumeDetails({ parsed }) {
  const [activeJd, setActiveJd] = useState('')

  if (!parsed) {
    return <div className="p-6 text-muted font-mono">No resume loaded yet.</div>
  }

  const contact = parsed.contact || {}
  const education = parsed.education || []
  const experience = parsed.experience || []
  const projects = parsed.projects || []
  const skills = parsed.skills || []
  const certifications = parsed.certifications || []
  const achievements = parsed.achievements || []
  const languages = parsed.languages || []

  // Extract raw text string from parsed resume JSON to calculate JD match score
  const fullResumeText = JSON.stringify(parsed)

  return (
    <div className="space-y-6">
      {/* 1. PHASE 2 DASHBOARD: JD Input, Match Percentage Gauge & Skill Gaps */}
      <JDMatchDashboard
        resumeText={fullResumeText}
        onActiveJdChange={setActiveJd}
      />

      {/* 2. PARSED RESUME DISPLAY */}
      <div className="rounded-xl border border-border bg-surface p-6 space-y-5">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-border bg-surface2 font-mono text-sm font-semibold text-accent">
            {initials(contact.name)}
          </div>
          <div>
            <h3 className="text-lg font-semibold">{contact.name || 'Name not detected'}</h3>
            <p className="text-sm text-muted font-mono">
              {[contact.email, contact.phone].filter(Boolean).join(' · ') || 'No contact info found'}
            </p>
            <p className="text-sm text-muted font-mono">
              {[contact.linkedin, contact.github].filter(Boolean).join(' · ')}
            </p>
          </div>
        </div>

        {skills.length > 0 && (
          <Section title={`Skills (${skills.length})`} icon="skills">
            <div>{skills.map((s, i) => <Tag key={i}>{s}</Tag>)}</div>
          </Section>
        )}

        {experience.length > 0 && (
          <Section title="Experience" icon="experience">
            {experience.map((e, i) => (
              <div key={i} className="mb-3">
                <p className="text-sm font-medium">{e.company} {e.role && `· ${e.role}`}</p>
                <p className="text-xs text-muted font-mono">{e.duration}</p>
                <ul className="mt-1 space-y-1 text-sm text-slate-300">
                  {e.bullets?.map((b, j) => (
                    <OptimizableBullet
                      key={j}
                      bullet={b}
                      targetJd={activeJd}
                      onApply={(newText) => {
                        e.bullets[j] = newText
                      }}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </Section>
        )}

        {projects.length > 0 && (
          <Section title="Projects" icon="projects">
            {projects.map((p, i) => {
              const projectBullets = Array.isArray(p.bullet_points)
                ? p.bullet_points.filter(Boolean)
                : []
              const fallbackDescription = p.description ? [p.description] : []
              const displayItems = projectBullets.length > 0 ? projectBullets : fallbackDescription

              return (
                <div key={i} className="mb-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium">{p.name}</p>
                    {p.date && <p className="text-xs text-muted font-mono whitespace-nowrap">{p.date}</p>}
                  </div>
                  {displayItems.length > 0 && (
                    <ul className="mt-1 space-y-1 text-sm text-slate-300">
                      {displayItems.map((item, j) => (
                        <OptimizableBullet
                          key={j}
                          bullet={item}
                          targetJd={activeJd}
                          onApply={(newText) => {
                            if (projectBullets.length > 0) {
                              p.bullet_points[j] = newText
                            } else {
                              p.description = newText
                            }
                          }}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              )
            })}
          </Section>
        )}

        {education.length > 0 && (
          <Section title="Education" icon="education">
            {education.map((e, i) => (
              <div key={i} className="mb-2 text-sm">
                <p className="font-medium">{e.institution}</p>
                <p className="text-muted">{[e.degree, e.year, e.gpa && `GPA ${e.gpa}`].filter(Boolean).join(' · ')}</p>
              </div>
            ))}
          </Section>
        )}

        {certifications.length > 0 && (
          <Section title="Certifications" icon="certifications">
            <div>{certifications.map((c, i) => <Tag key={i}>{c}</Tag>)}</div>
          </Section>
        )}

        {achievements.length > 0 && (
          <Section title="Achievements" icon="achievements">
            <ul className="space-y-1 text-sm text-slate-300">
              {achievements.map((a, i) => (
                <OptimizableBullet
                  key={i}
                  bullet={a}
                  targetJd={activeJd}
                  onApply={(newText) => {
                    achievements[i] = newText
                  }}
                />
              ))}
            </ul>
          </Section>
        )}

        {languages.length > 0 && (
          <Section title="Languages" icon="languages">
            <div>{languages.map((l, i) => <Tag key={i}>{l}</Tag>)}</div>
          </Section>
        )}
      </div>
    </div>
  )
}
