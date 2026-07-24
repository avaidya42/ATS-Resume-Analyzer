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
      <header className="border-b border-border px-6 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-mono text-lg font-semibold text-slate-100">
              Resume Intelligence Platform
            </h1>
            <p className="text-xs text-muted">Parse · Score · Optimize</p>
          </div>
          {result && (
            <button
              onClick={downloadJson}
              className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-accent hover:bg-surface2"
            >
              Export JSON
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {!result && (
          <UploadForm onUpload={handleUpload} loading={loading} error={error} />
        )}

        {result && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Fallback to 'result' directly if 'result.parsed' doesn't exist */}
            <ResumeDetails parsed={result?.parsed || result} />
            <ATSScore ats={result?.ats} />
          </div>
        )}

        {result && (
          <div className="mt-6">
            <button
              onClick={() => setResult(null)}
              className="text-xs font-mono text-muted hover:text-accent"
            >
              ← Analyze another resume
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
