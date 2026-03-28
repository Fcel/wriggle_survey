import { useState, useRef } from 'react'

export default function FileUpload({ onCompute, loading }) {
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef()

  function handleFile(f) {
    if (f && f.name.match(/\.(xlsx|xls)$/i)) setFile(f)
    else alert('Lütfen .xlsx veya .xls uzantılı bir dosya seçin.')
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  function handleSubmit() {
    if (file) onCompute(file)
  }

  return (
    <div className="upload-card">
      <h2 className="section-title">Import Data</h2>

      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div className="upload-icon">📂</div>
        <div className="upload-text">
          <strong>Dosya seçmek için tıklayın</strong> veya sürükleyip bırakın
        </div>
        <div className="upload-text" style={{ marginTop: '0.4rem', fontSize: '0.8rem' }}>
          Import Wriggle Survey &amp; Tunnel Axis Data.xlsx
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />
      </div>

      {file && (
        <div className="file-chosen">
          <span>📄</span>
          <span className="file-name">{file.name}</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {(file.size / 1024).toFixed(1)} KB
          </span>
          <button className="btn btn-secondary" style={{ padding: '0.3rem 0.65rem', fontSize: '0.8rem' }}
            onClick={e => { e.stopPropagation(); setFile(null) }}>
            ✕
          </button>
        </div>
      )}

      <div style={{ marginTop: '1rem' }}>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!file || loading}
        >
          {loading ? (
            <><div className="spinner" style={{ width: 16, height: 16 }} /> Hesaplanıyor...</>
          ) : (
            <> Hesapla</>
          )}
        </button>
      </div>
    </div>
  )
}
