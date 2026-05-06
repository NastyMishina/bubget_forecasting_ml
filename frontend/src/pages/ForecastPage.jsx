import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend as RechartsLegend,
} from 'recharts'
import Header from '../components/Header'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import client from '../api/client'


function fmtNum(v) {
  if (v == null || v === '...') return '—'
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
}

function MetricCard({ label, value, unit }) {
  return (
    <div className="metric-card">
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">
        {value != null ? Number(value).toFixed(4) : '—'}
      </div>
      {unit && <div className="metric-card__unit">{unit}</div>}
    </div>
  )
}

// CSV загрузка
function downloadCsv(chartData, filename = 'forecast.csv') {
  const header = 'period;base_forecast;optimistic_forecast;pessimistic_forecast\n'
  const rows = chartData
    .map((r) => {
      const base = r.base !== undefined && r.base !== null ? parseFloat(r.base).toFixed(2).replace('.', ',') : ''
      const pessimistic = r.pessimistic !== undefined && r.pessimistic !== null ? parseFloat(r.pessimistic).toFixed(2).replace('.', ',') : ''
      const optimistic = r.optimistic !== undefined && r.optimistic !== null ? parseFloat(r.optimistic).toFixed(2).replace('.', ',') : ''
      
      return `${r.period};${base};${optimistic};${pessimistic}`
    })
    .join('\n')
  const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// Парсинг даты из строки
function parseDate(dateStr) {
  if (!dateStr) return null
  
  // Формат DD.MM.YYYY
  const ddmmyyyy = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(dateStr)
  if (ddmmyyyy) {
    return new Date(ddmmyyyy[3], ddmmyyyy[2] - 1, ddmmyyyy[1])
  }
  
  // Формат YYYY-MM-DD
  const yyyymmdd = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr)
  if (yyyymmdd) {
    return new Date(yyyymmdd[1], yyyymmdd[2] - 1, yyyymmdd[3])
  }
  
  // Формат YYYY-MM
  const yyyymm = /^(\d{4})-(\d{2})$/.exec(dateStr)
  if (yyyymm) {
    return new Date(yyyymm[1], yyyymm[2] - 1, 1)
  }
  
  return null
}

// Форматирование даты для отображения
function formatDateForDisplay(dateObj) {
  if (!dateObj) return '—'
  const day = String(dateObj.getDate()).padStart(2, '0')
  const month = String(dateObj.getMonth() + 1).padStart(2, '0')
  const year = dateObj.getFullYear()
  return `${day}.${month}.${year}`
}

export default function ForecastPage() {
  const navigate   = useNavigate()
  const { userId } = useAuth()

  const [uploads,         setUploads]         = useState([])
  const [selectedUpload,  setSelectedUpload]  = useState('')
  const [targetColumn,    setTargetColumn]    = useState('target_kommerskie_rashody')

  const [loading,         setLoading]         = useState(false)
  const [loadingUploads,  setLoadingUploads]  = useState(false)
  const [error,           setError]           = useState('')
  const [result,          setResult]          = useState(null)

  useEffect(() => {
    if (!userId) return
    setLoadingUploads(true)
    client.get(`/api/data/uploads/${userId}`)
     .then(({ data }) => {
      const uploadsList = Array.isArray(data) ? data : (data.uploads || [])
      setUploads(uploadsList)
      })
      .catch(() => setError('Не удалось загрузить список файлов'))
      .finally(() => setLoadingUploads(false))
  }, [userId])

  const handleForecast = async () => {
    if (!selectedUpload) { setError('Выберите файл'); return }
    if (!targetColumn.trim()) { setError('Укажите целевую переменную'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const { data } = await client.post(
        `/api/forecasts/predict/${selectedUpload}?target_column=${encodeURIComponent(targetColumn)}`
      )
      console.log('=== ПОЛНЫЙ ОТВЕТ API ===')
      console.log(data)
      
      console.log('=== ПРОГНОЗЫ ===')
      console.log('predictions:', data.predictions)
      
      console.log('=== ПЕРИОДЫ (если есть) ===')
      console.log('periods:', data.periods)
      
      setResult(data)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail ?? 'Ошибка при выполнении прогноза')
    } finally {
      setLoading(false)
    }
  }

  // Построение визуализации прогнозов
  const chartData = (() => {
    if (!result) return []
    
    console.log('=== НАЧАЛО ПОСТРОЕНИЯ CHARTDATA ===')
    console.log('result:', result)
    
    const preds = result.predictions ?? {}
    console.log('predictions object:', preds)
    
    const base        = Array.isArray(preds.base)        ? preds.base.filter(v => v !== '...' && v != null) : []
    const optimistic  = Array.isArray(preds.optimistic)  ? preds.optimistic.filter(v => v !== '...' && v != null) : []
    const pessimistic = Array.isArray(preds.pessimistic) ? preds.pessimistic.filter(v => v !== '...' && v != null) : []

    console.log('Filtered arrays:')
    console.log('  base length:', base.length)
    console.log('  optimistic length:', optimistic.length)
    console.log('  pessimistic length:', pessimistic.length)

    // Получить периоды из результата (если доступны)
    const periods = result.periods ?? []
    console.log('periods from result:', periods)
    console.log('periods length:', periods.length)

    const mapped = base.map((v, i) => {
      const periodStr = periods[i] || String(i + 1)
      console.log(`Строка ${i}: periodStr="${periodStr}"`)
      
      const dateObj = parseDate(periodStr)
      console.log(`  parseDate результат:`, dateObj)
      
      const formattedDate = dateObj ? formatDateForDisplay(dateObj) : periodStr
      console.log(`  formattedDate="${formattedDate}"`)
      
      return {
        period:      formattedDate,
        periodRaw:   periodStr,
        base:        typeof v === 'number' ? v : parseFloat(v),
        optimistic:  typeof optimistic[i] === 'number' ? optimistic[i] : parseFloat(optimistic[i]),
        pessimistic: typeof pessimistic[i] === 'number' ? pessimistic[i] : parseFloat(pessimistic[i]),
      }
    })
    
    console.log('=== ИТОГОВЫЙ CHARTDATA ===')
    console.log(mapped)
    
    return mapped
  })()

  const metrics  = result?.metrics ?? {}
  const forecast_paths = result?.forecast_paths ?? {}

  return (
    <>
      <Header />
      <main className="page-content">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Назад
        </button>

        <div className="page-title">Прогнозирование бюджета</div>
        <div className="page-subtitle">
          Базовый · Оптимистичный · Пессимистичный сценарии
        </div>

        <ErrorMessage message={error} onClose={() => setError('')} />

        <div className="card card-body" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Файл с признаками</label>
              {loadingUploads ? (
                <div style={{ color: 'var(--muted)', fontSize: '.85rem' }}>Загрузка...</div>
              ) : (
                <select
                  className="form-control"
                  value={selectedUpload}
                  onChange={(e) => { setSelectedUpload(e.target.value); setResult(null) }}
                >
                  <option value="">— Выберите файл —</option>
                  {uploads.map((u) => (
                    <option key={u.id} value={u.id}>#{u.id} {u.filename}</option>
                  ))}
                </select>
              )}
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Целевая переменная</label>
              <input
                type="text"
                className="form-control"
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
                placeholder="target_kommerskie_rashody"
              />
            </div>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', gap: '.75rem', alignItems: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={handleForecast}
              disabled={loading || !selectedUpload}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  Вычисление прогноза...
                </>
              ) : (
                'Запустить прогноз'
              )}
            </button>
            {result && chartData.length > 0 && (
              <button
                className="btn btn-success"
                onClick={() => downloadCsv(chartData, `forecast_${selectedUpload}.csv`)}
              >
                Скачать спрогнозированные значения
              </button>
            )}
          </div>
        </div>

        {loading && (
          <LoadingSpinner text="Выполняется прогнозирование, подождите..." />
        )}

        {result && !loading && (
          <>
            {(metrics.r2_score != null || metrics.mae != null || metrics.rmse != null) && (
              <div style={{ marginBottom: '1.25rem' }}>
                <h3 style={{ fontSize: '.85rem', fontWeight: 600, marginBottom: '.75rem', color: 'var(--muted)' }}>
                  МЕТРИКИ МОДЕЛИ
                </h3>
                <div className="metrics-row">
                  <MetricCard label="R²"   value={metrics.r2_score} />
                  <MetricCard label="MAE"  value={metrics.mae} />
                  <MetricCard label="RMSE" value={metrics.rmse}/>
                </div>
              </div>
            )}

            {/* ── Chart ── */}
            {chartData.length > 0 && (
              <div className="chart-wrap">
                <div className="chart-title">
                  Прогноз: <strong>{result.target_column ?? targetColumn}</strong>
                  {result.forecast_id && (
                    <span style={{ marginLeft: '.75rem', color: 'var(--muted)', fontWeight: 400 }}>
                      (ID прогноза: #{result.forecast_id})
                    </span>
                  )}
                </div>
                <ResponsiveContainer width="100%" height={340}>
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="period"
                      tick={{ fontSize: 11 }}
                      label={{ value: 'Период', position: 'insideBottom', offset: -2, fontSize: 11 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => v.toLocaleString('ru-RU')} />
                    <Tooltip
                      formatter={(v, name) => [fmtNum(v), name]}
                      labelFormatter={(l) => `${l}`}
                    />
                    <RechartsLegend />
                    <Line
                      type="monotone"
                      dataKey="base"
                      name="Базовый"
                      stroke="#007bff"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="optimistic"
                      name="Пессимистичный"
                      stroke="#dc3545"
                      strokeWidth={1.8}
                      strokeDasharray="5 3"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="pessimistic"
                      name="Оптимистичный"
                      stroke="#28a745"
                      strokeWidth={1.8}
                      strokeDasharray="5 3"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* ── Table ── */}
            {chartData.length > 0 && (
              <div className="card" style={{ marginBottom: '1.25rem' }}>
                <div className="card-header">Таблица прогноза</div>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Период</th>
                        <th>Базовый</th>
                        <th>Оптимистичный</th>
                        <th>Пессимистичный</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chartData.map((row, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 500 }}>{row.period}</td>
                          <td style={{ color: '#007bff'  }}>{fmtNum(row.base)}</td>
                          <td style={{ color: '#28a745' }}>{fmtNum(row.pessimistic)}</td>
                          <td style={{ color: '#dc3545'  }}>{fmtNum(row.optimistic)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </>
  )
}