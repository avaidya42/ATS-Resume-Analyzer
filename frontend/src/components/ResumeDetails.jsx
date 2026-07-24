import { useState } from 'react'
import JDMatchDashboard from './JDMatchDashboard'
import OptimizableBullet from './BulletOptimizer'

function Section({ title, children }) {
  return (
    <div className="border-t border-border pt-4 first:border-t-0 first:pt-0">
      <h4 className="font-mono text-xs uppercase tracking-widest text-muted mb-2">{title}</h4>
      {children}
    </div>
  )
}

function Tag({ children }) {
  return (
    <span className="inline-block rounded-md border border-border bg-surface2 px-2 py-1 text-xs mr-2 mb-2">
      {children}
    </span>
  )
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
        <div>
          <h3 className="text-lg font-semibold">{contact.name || 'Name not detected'}</h3>
          <p className="text-sm text-muted font-mono">
            {[contact.email, contact.phone].filter(Boolean).join(' · ') || 'No contact info found'}
          </p>
          <p className="text-sm text-muted font-mono">
            {[contact.linkedin, contact.github].filter(Boolean).join(' · ')}
          </p>
        </div>

        {skills.length > 0 && (
          <Section title={`Skills (${skills.length})`}>
            <div>{skills.map((s, i) => <Tag key={i}>{s}</Tag>)}</div>
          </Section>
        )}

        {experience.length > 0 && (
          <Section title="Experience">
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
          <Section title="Projects">
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
          <Section title="Education">
            {education.map((e, i) => (
              <div key={i} className="mb-2 text-sm">
                <p className="font-medium">{e.institution}</p>
                <p className="text-muted">{[e.degree, e.year, e.gpa && `GPA ${e.gpa}`].filter(Boolean).join(' · ')}</p>
              </div>
            ))}
          </Section>
        )}

        {certifications.length > 0 && (
          <Section title="Certifications">
            <div>{certifications.map((c, i) => <Tag key={i}>{c}</Tag>)}</div>
          </Section>
        )}

        {achievements.length > 0 && (
          <Section title="Achievements">
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
          <Section title="Languages">
            <div>{languages.map((l, i) => <Tag key={i}>{l}</Tag>)}</div>
          </Section>
        )}
      </div>
    </div>
  )
}