import { useRef, useState } from 'react'

export default function UploadForm({ onUpload, loading, error }) {
  const [dragActive, setDragActive] = useState(false)
  const [fileName, setFileName] = useState(null)
  const inputRef = useRef(null)

  const handleFile = (file) => {
    if (!file) return
    setFileName(file.name)
    onUpload(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  return (
    <div className="mx-auto w-full max-w-xl">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`group cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors
          ${dragActive ? 'border-accent bg-accent/5' : 'border-border bg-surface hover:border-accent/60'}`}
      >
        <div
          className={`mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border transition-colors
            ${dragActive ? 'border-accent/50 bg-accent/10 text-accent' : 'border-border bg-surface2 text-muted group-hover:text-accent'}`}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <p className="font-mono text-sm text-slate-200">
          {fileName ? fileName : 'Drop your resume PDF here, or click to browse'}
        </p>
        <p className="mt-2 text-xs text-muted/70">PDF only · max 5MB</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      {loading && (
        <div className="mt-4 flex items-center justify-center gap-2 font-mono text-sm text-accent">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          Parsing resume and computing ATS score…
        </div>
      )}
      {error && (
        <p className="mt-4 text-center font-mono text-sm text-red-400">{error}</p>
      )}
    </div>
  )
}
