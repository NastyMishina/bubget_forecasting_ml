import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import client from '../api/client'

// Определяем массив знаачений для легенды графиков
const LEGEND = [
  { color: '#2563EB', label: 'Observed',  desc: 'Исходный временной ряд без изменений' },
  { color: '#16A34A', label: 'Trend',     desc: 'Долгосрочное направление изменений' },
  { color: '#D97706', label: 'Seasonal',  desc: 'Повторяющийся сезонный паттерн' },
  { color: '#DC2626', label: 'Residual',  desc: 'Остаток' },
]

// Перебираю элементы массива легенды для отрисовки
function Legend() {
  return (
    <div className="decomp-legend">
      {LEGEND.map(({ color, label, desc }) => (
        <div className="decomp-legend__item" key={label}>
          <div className="decomp-legend__dot" style={{ background: color }} />
          <div>
            <strong>{label}</strong>
            <span style={{ color: 'var(--muted)', marginLeft: '.35rem' }}>{desc}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// Проверяю наличие созданного графика, если нет - выводим текст
function FeatureImage({ name, dataUri }) {
  if (!dataUri) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--muted)', fontSize: '.85rem' }}>
        Изображение недоступно
      </div>
    )
  }
  return <img className="decomp-item__img" src={dataUri} alt={`Декомпозиция: ${name}`} />
}

// Инициализирую переменные состояний
export default function DecompositionPage() {
  const navigate   = useNavigate()
  const { userId } = useAuth()

  const [uploads,       setUploads]       = useState([])
  const [selectedUpload, setSelectedUpload] = useState('')
  const [selectedFeature, setSelectedFeature] = useState('')
  const [period,        setPeriod]        = useState(4)

  const [loading,       setLoading]       = useState(false)
  const [loadingUploads, setLoadingUploads] = useState(false)
  const [error,         setError]         = useState('')
  const [result,        setResult]        = useState(null) 

  const featureNames = result ? Object.keys(result.decomposition.plot_data || {}) : []

  //
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



  const handleDecompose = async () => {
    if (!selectedUpload) { setError('Выберите файл'); return }
    setLoading(true); setError(''); setResult(null); setSelectedFeature('')
    try {
      const { data } = await client.post(
        `/api/data/decompose/${selectedUpload}?period=${period}`
      )
      setResult(data)
      const names = Object.keys(data.decomposition?.plot_data || {})
      if (names.length) setSelectedFeature(names[0])
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail ?? 'Ошибка декомпозиции')
    } finally {
      setLoading(false)
    }
  }

  const currentImage = result?.decomposition?.plot_data?.[selectedFeature] ?? null

  return (
    <>
      <Header />
      <main className="page-content">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Назад
        </button>

        <div className="page-title">Декомпозиция временных рядов</div>
        <div className="page-subtitle">
          Разложение на компоненты: тренд, сезонность и остатки (seasonal_decompose)
        </div>

        <ErrorMessage message={error} onClose={() => setError('')} />

        <div className="card card-body" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Файл с данными</label>
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
                    <option key={u.id} value={u.id}>
                      #{u.id} {u.filename}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Период сезонности</label>
              <select
                className="form-control"
                value={period}
                onChange={(e) => setPeriod(Number(e.target.value))}
              >
                <option value={4}>4 (квартальный)</option>
                <option value={12}>12 (месячный)</option>
                <option value={2}>2 (полугодовой)</option>
              </select>
            </div>

            {result && featureNames.length > 0 && (
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Признак для отображения</label>
                <select
                  className="form-control"
                  value={selectedFeature}
                  onChange={(e) => setSelectedFeature(e.target.value)}
                >
                  {featureNames.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div style={{ marginTop: '1rem' }}>
            <button
              className="btn btn-primary"
              onClick={handleDecompose}
              disabled={loading || !selectedUpload}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  Вычисление...
                </>
              ) : (
                'Построить графики'
              )}
            </button>
          </div>
        </div>

        {loading && (
          <LoadingSpinner text="Выполняется декомпозиция временных рядов..." />
        )}

        {result && !loading && (
          <>
            <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
              Процесс расчета и построения графиков завершен за {result.processing_time_sec}с.
              Разложено признаков: <strong>{result.decomposition.features_decomposed}</strong>
              {Object.keys(result.decomposition.errors || {}).length > 0 && (
                <span style={{ marginLeft: '1rem', color: 'var(--danger)' }}>
                  Ошибок: {Object.keys(result.decomposition.errors).length}
                </span>
              )}
            </div>

            {selectedFeature && (
              <div className="card" style={{ marginBottom: '1.25rem' }}>
                <div className="decomp-item__title">
                  <span>Декомпозиция: <strong>{selectedFeature}</strong></span>
                  <span style={{ marginLeft: 'auto', fontSize: '.78rem', color: 'var(--muted)' }}>
                    Модель: {result.model} · Период: {result.period}
                  </span>
                </div>
                <FeatureImage name={selectedFeature} dataUri={currentImage} />
              </div>
            )}

            <Legend />


            {featureNames.length > 1 && (
              <div style={{ marginTop: '1.5rem' }}>
                <h3 style={{ fontSize: '.9rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--muted)' }}>
                  Все признаки ({featureNames.length})
                </h3>
                <div className="decomp-grid">
                  {featureNames.map((name) => (
                    <div
                      key={name}
                      className="decomp-item"
                      style={{
                        cursor: 'pointer',
                        outline: name === selectedFeature ? '2px solid var(--primary)' : 'none',
                      }}
                      onClick={() => setSelectedFeature(name)}
                    >
                      <div className="decomp-item__title">
                        <span>{name}</span>
                      </div>
                      <FeatureImage name={name} dataUri={result.decomposition.plot_data[name]} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Errors */}
            {Object.keys(result.decomposition.errors || {}).length > 0 && (
              <div style={{ marginTop: '1.5rem' }}>
                <div className="alert alert-danger">
                  <div>
                    <strong>Ошибки декомпозиции:</strong>
                    <ul style={{ margin: '.5rem 0 0 1rem' }}>
                      {Object.entries(result.decomposition.errors).map(([feat, msg]) => (
                        <li key={feat} style={{ fontSize: '.82rem' }}>
                          <strong>{feat}:</strong> {msg}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </>
  )
}
