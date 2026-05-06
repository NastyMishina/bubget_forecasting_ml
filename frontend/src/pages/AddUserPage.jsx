// frontend/src/pages/AddUserPage.jsx
/**
 * Страница добавления нового пользователя (только для ADMIN)
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
import client from '../api/client'

export default function AddUserPage() {
  const navigate = useNavigate()
  const { role } = useAuth()

  // ✅ Проверка что это администратор
  if (role !== 'admin') {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Доступ запрещен</div>
  }

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    full_name: '',
    role: 'analyst', // По умолчанию analyst
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Валидация
    if (!formData.username.trim()) {
      setError('Укажите имя пользователя')
      return
    }
    if (!formData.email.trim()) {
      setError('Укажите email')
      return
    }
    if (formData.password !== formData.password_confirm) {
      setError('Пароли не совпадают')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      // ✅ Используем /api/users с полной информацией
      await client.post('/api/users', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
        role: formData.role,
      })
      setSuccess('Пользователь успешно добавлен!')
      // ✅ Редирект на /admin
      setTimeout(() => navigate('/admin'), 2000)
    } catch (err) {
      console.error('Error details:', err)
      let errorMessage = 'Ошибка при добавлении пользователя'
    
    if (err.response?.data?.detail) {
      // Если detail - строка
      if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      }
      // Если detail - массив ошибок валидации
      else if (Array.isArray(err.response.data.detail)) {
        errorMessage = err.response.data.detail
          .map(e => `${e.loc?.[1] || 'field'}: ${e.msg}`)
          .join(', ')
      }
    }
    
    setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header />
      <main className="page-content">
        <button className="back-btn" onClick={() => navigate('/admin')}>
          ← Назад
        </button>

        <div style={{ textAlign: 'center' }}>
        <div className="page-title">Добавить пользователя</div>
        <div className="page-subtitle">Создать новый профиль пользователя</div>
        </div>

        <ErrorMessage message={error} onClose={() => setError('')} />
        <SuccessMessage message={success} onClose={() => setSuccess('')} />

        <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '60vh',
        width: '100%'  
          }}>

        <div className="card card-body" style={{ maxWidth: '500px', width: '100%' }}>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Имя пользователя *</label>
              <input
                type="text"
                className="form-control"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="ivan_ivanov"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Email *</label>
              <input
                type="email"
                className="form-control"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="ivan@example.com"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Полное имя</label>
              <input
                type="text"
                className="form-control"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                placeholder="Иван Иванов"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Пароль *</label>
              <input
                type="password"
                className="form-control"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="●●●●●●"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Подтверждение пароля *</label>
              <input
                type="password"
                className="form-control"
                name="password_confirm"
                value={formData.password_confirm}
                onChange={handleChange}
                placeholder="●●●●●●"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Роль *</label>
              <select
                className="form-control"
                name="role"
                value={formData.role}
                onChange={handleChange}
                disabled={loading}
              >
                <option value="analyst">Analyst (аналитик - доступ к анализу)</option>
                <option value="admin">Admin (администратор - полный доступ)</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Добавление...' : 'Добавить пользователя'}
              </button>
              {/* ✅ Кнопка отмены ведёт на /admin */}
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate('/admin')}
                disabled={loading}
              >
                Отмена
              </button>
            </div>
          </form>
          </div>
        </div>
      </main>
    </>
  )
}