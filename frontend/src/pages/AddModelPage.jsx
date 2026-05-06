// frontend/src/pages/AddModelPage.jsx
/**
 * Страница добавления новой ML модели (только для ADMIN)
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
import client from '../api/client'

export default function AddModelPage() {
  const navigate = useNavigate()
  const { role } = useAuth()

  // ✅ Проверка что это администратор
  if (role !== 'admin') {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Доступ запрещен</div>
  }

  const [formData, setFormData] = useState({
    algorithm: 'ridge',
    version: '1.0',
    file: null,
    mae: '',
    rmse: '',
    r2_score: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleFileChange = (e) => {
    setFormData(prev => ({ ...prev, file: e.target.files[0] }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!formData.file) {
      setError('Выберите файл модели')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const fd = new FormData()
      fd.append('algorithm', formData.algorithm)
      fd.append('version', formData.version)
      fd.append('model_file', formData.file)
      fd.append('mae', formData.mae || '0')
      fd.append('rmse', formData.rmse || '0')
      fd.append('r2_score', formData.r2_score || '0')

      await client.post('/api/models', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setSuccess('Модель успешно добавлена!')
      setTimeout(() => navigate('/dashboard'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при добавлении модели')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header />
      <main className="page-content">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Назад
        </button>

        <div className="page-title">Добавить ML модель</div>
        <div className="page-subtitle">Загрузить новую предобученную модель</div>

        <ErrorMessage message={error} onClose={() => setError('')} />
        <SuccessMessage message={success} onClose={() => setSuccess('')} />

        <div className="card card-body" style={{ maxWidth: '500px' }}>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Алгоритм *</label>
              <select
                className="form-control"
                name="algorithm"
                value={formData.algorithm}
                onChange={handleChange}
              >
                <option value="ridge">Ridge Regression</option>
                <option value="xgboost">XGBoost</option>
                <option value="random_forest">Random Forest</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Версия *</label>
              <input
                type="text"
                className="form-control"
                name="version"
                value={formData.version}
                onChange={handleChange}
                placeholder="1.0"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Файл модели (*.pkl) *</label>
              <input
                type="file"
                className="form-control"
                accept=".pkl"
                onChange={handleFileChange}
                required
              />
              {formData.file && (
                <div style={{ fontSize: '.8rem', color: 'var(--muted)', marginTop: '.5rem' }}>
                  {formData.file.name}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">MAE (Mean Absolute Error)</label>
              <input
                type="number"
                className="form-control"
                name="mae"
                value={formData.mae}
                onChange={handleChange}
                placeholder="0.0"
                step="0.0001"
              />
            </div>

            <div className="form-group">
              <label className="form-label">RMSE (Root Mean Squared Error)</label>
              <input
                type="number"
                className="form-control"
                name="rmse"
                value={formData.rmse}
                onChange={handleChange}
                placeholder="0.0"
                step="0.0001"
              />
            </div>

            <div className="form-group">
              <label className="form-label">R² Score</label>
              <input
                type="number"
                className="form-control"
                name="r2_score"
                value={formData.r2_score}
                onChange={handleChange}
                placeholder="0.0"
                step="0.0001"
                min="0"
                max="1"
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Добавление...' : 'Добавить модель'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate('/dashboard')}
                disabled={loading}
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </main>
    </>
  )
}