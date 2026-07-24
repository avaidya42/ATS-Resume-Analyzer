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
    <div className="w-full max-w-xl mx-auto">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors
          ${dragActive ? 'border-accent bg-accent/5' : 'border-border bg-surface hover:border-accent/60'}`}
      >
        <p className="font-mono text-sm text-muted">
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
        <p className="mt-4 text-center font-mono text-sm text-accent animate-pulse">
          Parsing resume and computing ATS score…
        </p>
      )}
      {error && (
        <p className="mt-4 text-center font-mono text-sm text-red-400">{error}</p>
      )}
    </div>
  )
}
