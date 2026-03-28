import { useState } from 'react'
import FileUpload from './components/FileUpload.jsx'
import ResultsView from './components/ResultsView.jsx'

export default function App() {
  const [diaDesign, setDiaDesign] = useState(3.396)
  const [direction, setDirection] = useState('DIRECT')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [chartData, setChartData] = useState(null)
  const [downloadId, setDownloadId] = useState(null)

  async function handleCompute(file) {
    setLoading(true)
    setError(null)
    setResults(null)
    setChartData(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('dia_design', diaDesign)
    formData.append('direction', direction)

    try {
      const res = await fetch('/api/compute', { method: 'POST', body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Hesaplama başarısız')
      setResults(data.results)
      setChartData(data.chart_data)
      setDownloadId(data.download_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="header-logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="14" stroke="#60a5fa" strokeWidth="2.5" strokeDasharray="4 2"/>
              <circle cx="16" cy="16" r="2.5" fill="#60a5fa"/>
              <line x1="16" y1="2" x2="16" y2="8" stroke="#60a5fa" strokeWidth="2"/>
              <line x1="16" y1="24" x2="16" y2="30" stroke="#60a5fa" strokeWidth="2"/>
              <line x1="2" y1="16" x2="8" y2="16" stroke="#60a5fa" strokeWidth="2"/>
              <line x1="24" y1="16" x2="30" y2="16" stroke="#60a5fa" strokeWidth="2"/>
            </svg>
            <span>Wriggle Survey</span>
          </div>
          <span className="header-sub">Best-Fit Circle 3D — Tunnel Survey Analysis</span>
        </div>
      </header>

      <main className="app-main">
        <section className="config-card">
          <h2 className="section-title">Configuration</h2>
          <div className="config-row">
            <div className="form-group">
              <label>Design Diameter (m)</label>
              <input
                type="number"
                step="0.001"
                value={diaDesign}
                onChange={e => setDiaDesign(parseFloat(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label>Excavation Direction</label>
              <select value={direction} onChange={e => setDirection(e.target.value)}>
                <option value="DIRECT">DIRECT</option>
                <option value="REVERSE">REVERSE</option>
              </select>
            </div>
          </div>
        </section>

        <FileUpload onCompute={handleCompute} loading={loading} />

        {error && (
          <div className="error-box">
            <strong>Hata:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading-box">
            <div className="spinner" />
            <span>Hesaplanıyor...</span>
          </div>
        )}

        {results && chartData && (
          <ResultsView
            results={results}
            chartData={chartData}
            downloadId={downloadId}
            diaDesign={diaDesign}
          />
        )}
      </main>

      <footer className="app-footer">
        Wriggle Survey — Best-Fit Circle 3D (Kasa Method) | Survey Engineering Tool
      </footer>
    </div>
  )
}
