import { useState } from 'react'
import UploadForm from '../components/UploadForm.jsx'
import ResumeDetails from '../components/ResumeDetails.jsx'
import ATSScore from '../components/ATSScore.jsx'
import { uploadResume } from '../api/resumeApi.js'

export default function Dashboard() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleUpload = async (file) => {
    setLoading(true)
    setError(null)
    try {
      const data = await uploadResume(file)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze resume.')
    } finally {
      setLoading(false)
    }
  }

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url

    // Safely fallback whether backend returns nested result.parsed or flat parsed object
    const contactName = result?.parsed?.contact?.name || result?.contact?.name || 'resume'
    a.download = `${contactName}-analysis.json`

    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-border bg-base/80 px-6 py-5 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface font-mono text-sm font-semibold text-accent">
              R/
            </div>
            <div>
              <h1 className="font-mono text-lg font-semibold leading-tight text-slate-100">
                Resume Intelligence Platform
              </h1>
              <p className="text-xs text-muted">Parse · Score · Optimize</p>
            </div>
          </div>
          {result && (
            <button
              onClick={downloadJson}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 font-mono text-xs text-accent transition hover:border-accent/50 hover:bg-surface2"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export JSON
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        {!result && (
          <div className="py-10">
            <div className="mx-auto mb-10 max-w-xl text-center">
              <h2 className="text-2xl font-semibold text-slate-100">
                See your resume the way a hiring pipeline does
              </h2>
              <p className="mt-2 text-sm text-muted">
                Upload a PDF to get an ATS compatibility score, a job-description
                skill-gap analysis, and AI-assisted bullet rewrites — all in one pass.
              </p>
            </div>
            <UploadForm onUpload={handleUpload} loading={loading} error={error} />
          </div>
        )}

        {result && (
          <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Fallback to 'result' directly if 'result.parsed' doesn't exist */}
              <ResumeDetails parsed={result?.parsed || result} />
              <ATSScore ats={result?.ats} />
            </div>

            <div className="mt-8 flex items-center gap-2 border-t border-border pt-6">
              <button
                onClick={() => setResult(null)}
                className="inline-flex items-center gap-1.5 font-mono text-xs text-muted transition hover:text-accent"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="19" y1="12" x2="5" y2="12" />
                  <polyline points="12 19 5 12 12 5" />
                </svg>
                Analyze another resume
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
