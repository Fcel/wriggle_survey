import { useState, useMemo } from 'react'
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ReferenceLine, ScatterChart, Scatter,
  Cell
} from 'recharts'

const fmt = (v, d = 4) => (v == null ? '—' : Number(v).toFixed(d))

// Generate circle outline as {x, y} points
function makeCircle(cx, cy, r, n = 120) {
  const pts = []
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * 2 * Math.PI
    pts.push({ x: cx + r * Math.sin(a), y: cy + r * Math.cos(a) })
  }
  return pts
}

// ─── Results Table ──────────────────────────────────────────────────────────
function ResultsTable({ results }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ring No.</th>
            <th>Easting (m)</th>
            <th>Northing (m)</th>
            <th>Elevation (m)</th>
            <th>Chainage (m)</th>
            <th>Hor. Dev. (m)</th>
            <th>Ver. Dev. (m)</th>
            <th>Avg. Radius (m)</th>
            <th>Avg. Diameter (m)</th>
          </tr>
        </thead>
        <tbody>
          {results.map((row, i) => {
            const dh = Number(row['HOR.DEVIATION (M.)'])
            const dv = Number(row['VER.DEVIATION (M.)'])
            return (
              <tr key={i}>
                <td><strong>{row['RING NO.']}</strong></td>
                <td>{fmt(row['TUN.CL-EASTING (M.)'], 3)}</td>
                <td>{fmt(row['TUN.CL-NORTHING (M.)'], 3)}</td>
                <td>{fmt(row['TUN.CL-ELEVATION (M.)'], 3)}</td>
                <td>{fmt(row['CHAINAGE (M.)'], 3)}</td>
                <td className={dh >= 0 ? 'val-pos' : 'val-neg'}>{fmt(dh)}</td>
                <td className={dv >= 0 ? 'val-pos' : 'val-neg'}>{fmt(dv)}</td>
                <td>{fmt(row['AVG.RADIUS (M.)'])}</td>
                <td>{fmt(row['AVG.DIAMETER (M.)'])}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Deviation Charts ───────────────────────────────────────────────────────
function DeviationCharts({ chartData }) {
  const data = chartData.map(d => ({
    ring: d.ring_no,
    hor: d.hor_deviation != null ? +d.hor_deviation.toFixed(4) : null,
    ver: d.ver_deviation != null ? +d.ver_deviation.toFixed(4) : null,
  }))

  const tooltipStyle = {
    background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
    color: '#e2e8f0', fontSize: '0.82rem'
  }

  return (
    <div className="charts-grid">
      <div>
        <div className="chart-title">Horizontal Deviation (m)</div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="ring" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={v => v.toFixed(3)} />
              <Tooltip contentStyle={tooltipStyle} formatter={v => [v.toFixed(4) + ' m', 'Hor. Dev.']} />
              <ReferenceLine y={0} stroke="#475569" />
              <Bar dataKey="hor" radius={[4, 4, 0, 0]}>
                {data.map((d, i) => (
                  <Cell key={i} fill={d.hor >= 0 ? '#4ade80' : '#f87171'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <div className="chart-title">Vertical Deviation (m)</div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="ring" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={v => v.toFixed(3)} />
              <Tooltip contentStyle={tooltipStyle} formatter={v => [v.toFixed(4) + ' m', 'Ver. Dev.']} />
              <ReferenceLine y={0} stroke="#475569" />
              <Bar dataKey="ver" radius={[4, 4, 0, 0]}>
                {data.map((d, i) => (
                  <Cell key={i} fill={d.ver >= 0 ? '#4ade80' : '#f87171'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ─── Diameter Chart ──────────────────────────────────────────────────────────
function DiameterChart({ chartData, diaDesign }) {
  const data = chartData.map(d => ({
    ring: d.ring_no,
    diameter: d.avg_radius != null ? +(d.avg_radius * 2).toFixed(4) : null,
  }))

  const tooltipStyle = {
    background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
    color: '#e2e8f0', fontSize: '0.82rem'
  }

  return (
    <div>
      <div className="chart-title">Average Diameter vs Design (m)</div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="ring" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={v => v.toFixed(3)}
              domain={['auto', 'auto']}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={v => [v.toFixed(4) + ' m']} />
            <Legend
              wrapperStyle={{ fontSize: '0.8rem', color: '#94a3b8' }}
              formatter={v => v === 'diameter' ? 'Avg. Diameter' : 'Design'}
            />
            <ReferenceLine y={diaDesign} stroke="#f59e0b" strokeDasharray="5 3"
              label={{ value: `Design ${diaDesign}m`, fill: '#f59e0b', fontSize: 11, position: 'right' }} />
            <Line
              type="monotone" dataKey="diameter"
              stroke="#60a5fa" strokeWidth={2} dot={{ fill: '#60a5fa', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ─── Cross-Section Chart ─────────────────────────────────────────────────────
function CrossSectionChart({ chartData }) {
  const [selectedIdx, setSelectedIdx] = useState(0)

  const ring = chartData[selectedIdx]

  const scatterData = ring.points.map(p => ({ x: p.x, y: p.y, label: p.label }))
  const fitCircle  = useMemo(() => makeCircle(0, 0, ring.avg_radius), [ring])
  const desCircle  = useMemo(() => makeCircle(0, 0, ring.design_radius), [ring])

  const tooltipStyle = {
    background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
    color: '#e2e8f0', fontSize: '0.82rem'
  }

  const CustomDot = (props) => {
    const { cx, cy, payload } = props
    return (
      <g>
        <circle cx={cx} cy={cy} r={5} fill="#f97316" stroke="#1e293b" strokeWidth={1.5} />
        <text x={cx + 8} y={cy + 4} fill="#94a3b8" fontSize={10}>{payload.label}</text>
      </g>
    )
  }

  return (
    <div>
      <div className="ring-selector">
        <label>Ring:</label>
        <select value={selectedIdx} onChange={e => setSelectedIdx(Number(e.target.value))}>
          {chartData.map((d, i) => (
            <option key={i} value={i}>{d.ring_no} — CH {d.chainage?.toFixed(2)}</option>
          ))}
        </select>
      </div>

      <div className="cross-section-wrap">
        <div className="cross-section-chart">
          <div className="chart-title">Tunnel Cross-Section — {ring.ring_no}</div>
          <div style={{ width: '100%', height: 360 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  type="number" dataKey="x" name="X"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={v => v.toFixed(2)}
                  label={{ value: 'Horizontal (m)', fill: '#64748b', fontSize: 11, position: 'insideBottom', offset: -4 }}
                />
                <YAxis
                  type="number" dataKey="y" name="Y"
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={v => v.toFixed(2)}
                  label={{ value: 'Vertical (m)', fill: '#64748b', fontSize: 11, angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  cursor={{ strokeDasharray: '3 3', stroke: '#475569' }}
                  formatter={(v, name) => [v.toFixed(4) + ' m', name]}
                />
                {/* Design circle */}
                <Scatter
                  name="Design Circle"
                  data={desCircle}
                  fill="none"
                  line={{ stroke: '#f59e0b', strokeWidth: 1.5, strokeDasharray: '6 3' }}
                  shape={() => null}
                />
                {/* Best-fit circle */}
                <Scatter
                  name="Best-fit Circle"
                  data={fitCircle}
                  fill="none"
                  line={{ stroke: '#60a5fa', strokeWidth: 2 }}
                  shape={() => null}
                />
                {/* Measured points */}
                <Scatter
                  name="Measured Points"
                  data={scatterData}
                  fill="#f97316"
                  shape={<CustomDot />}
                />
                {/* Center */}
                <Scatter
                  name="Center"
                  data={[{ x: 0, y: 0 }]}
                  fill="#e2e8f0"
                  shape={props => (
                    <g>
                      <line x1={props.cx - 6} y1={props.cy} x2={props.cx + 6} y2={props.cy} stroke="#e2e8f0" strokeWidth={1.5} />
                      <line x1={props.cx} y1={props.cy - 6} x2={props.cx} y2={props.cy + 6} stroke="#e2e8f0" strokeWidth={1.5} />
                    </g>
                  )}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="cross-section-legend">
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#f97316' }} />
            <span>Measured Points</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#60a5fa' }} />
            <span>Best-fit Circle (Kasa)</span>
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: '#f59e0b', opacity: 0.7 }} />
            <span>Design Circle</span>
          </div>
          <table className="deviation-table" style={{ marginTop: '1rem' }}>
            <tbody>
              <tr>
                <td>Chainage</td>
                <td><strong>{ring.chainage?.toFixed(3)} m</strong></td>
              </tr>
              <tr>
                <td>Avg. Radius</td>
                <td><strong>{ring.avg_radius?.toFixed(4)} m</strong></td>
              </tr>
              <tr>
                <td>Design Radius</td>
                <td><strong>{ring.design_radius?.toFixed(4)} m</strong></td>
              </tr>
              <tr>
                <td>Hor. Deviation</td>
                <td style={{ color: ring.hor_deviation >= 0 ? '#4ade80' : '#f87171' }}>
                  <strong>{ring.hor_deviation?.toFixed(4)} m</strong>
                </td>
              </tr>
              <tr>
                <td>Ver. Deviation</td>
                <td style={{ color: ring.ver_deviation >= 0 ? '#4ade80' : '#f87171' }}>
                  <strong>{ring.ver_deviation?.toFixed(4)} m</strong>
                </td>
              </tr>
              <tr>
                <td>Points</td>
                <td><strong>{ring.points.length}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Main Results View ────────────────────────────────────────────────────────
export default function ResultsView({ results, chartData, downloadId, diaDesign }) {
  const [tab, setTab] = useState('table')

  const tabs = [
    { id: 'table',   label: 'Results Table' },
    { id: 'dev',     label: 'Deviations' },
    { id: 'dia',     label: 'Diameter' },
    { id: 'section', label: 'Cross-Section' },
  ]

  return (
    <div className="results-card">
      <div className="results-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="results-title">Computation Results</span>
          <span className="badge">{results.length} rings</span>
        </div>
        {downloadId && (
          <a
            href={`/api/download/${downloadId}`}
            download="Export_Wriggle_Survey.xlsx"
            className="btn btn-success"
          >
            ⬇ Excel İndir
          </a>
        )}
      </div>

      <div className="tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'table'   && <ResultsTable results={results} />}
      {tab === 'dev'     && <DeviationCharts chartData={chartData} />}
      {tab === 'dia'     && <DiameterChart chartData={chartData} diaDesign={diaDesign} />}
      {tab === 'section' && <CrossSectionChart chartData={chartData} />}
    </div>
  )
}
