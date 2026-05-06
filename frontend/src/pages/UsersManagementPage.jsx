// frontend/src/components/UsersManagementPage.jsx

{/*
  import { useState, useEffect } from 'react'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import client from '../api/client'

function StatusBadge({ role }) {
  const map = {
    admin: { cls: 'badge-danger', label: 'Admin' },
    analyst: { cls: 'badge-success', label: 'Analyst' },
  }
  const { cls, label } = map[role] ?? { cls: 'badge-secondary', label: role }
  return <span className={`badge ${cls}`}>{label}</span>
}

function formatDate(dateString) {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleString('ru-RU', { 
    dateStyle: 'short', 
    timeStyle: 'short' 
  })
}

export default function UsersManagementPage() {
  const [users, setUsers] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const fetchUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await client.get('/api/users')
      setUsers(response.data)
      console.log('Users fetched:', response.data)
    } catch (err) {
      console.error('Fetch users error:', err)
      setError(err.response?.data?.detail ?? 'Ошибка при загрузке пользователей')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUsers() }, [])

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected(
      selected.size === users.length ? new Set() : new Set(users.map((u) => u.id))
    )
  }

  const handleDelete = async () => {
    if (!selected.size) return
    if (!window.confirm(`Удалить ${selected.size} пользователей?`)) return

    setError('')
    setSuccess('')
    setDeleting(true)

    try {
      const userIds = Array.from(selected)
      
      await Promise.all(
        userIds.map((userId) => {
          console.log(`Deleting user ${userId}`)
          return client.delete(`/api/users/${userId}`)
        })
      )

      setSuccess(`${selected.size} пользователей удалено`)
      setSelected(new Set())
      fetchUsers()
    } catch (err) {
      console.error('Delete error:', err)
      setError(err.response?.data?.detail ?? 'Ошибка при удалении пользователей')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <ErrorMessage message={error} onClose={() => setError('')} />
      <SuccessMessage message={success} onClose={() => setSuccess('')} />

      <div className="toolbar">
        {selected.size > 0 && (
          <button 
            className="btn btn-danger" 
            onClick={handleDelete}
            disabled={deleting}
          >
            🗑 Удалить выбранных ({selected.size})
          </button>
        )}
        <button 
          className="btn btn-secondary toolbar-right" 
          onClick={fetchUsers}
          disabled={loading}
        >
          <img src="/icons/icon-refresh.png" alt="refresh" style={{ width: "16px", marginRight: "6px" }} />
          Обновить
        </button>
      </div>

      {loading ? (
        <LoadingSpinner text="Загрузка пользователей..." />
      ) : users.length === 0 ? (
        <div className="empty-state card card-body">
          <div style={{ display: "flex", justifyContent: "center" }}>
            <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
          </div>
          <div className="empty-state__text">Нет пользователей в системе.</div>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 40 }}>
                    <input
                      type="checkbox"
                      checked={selected.size === users.length && users.length > 0}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>ID</th>
                  <th>Имя пользователя</th>
                  <th>Email</th>
                  <th>Полное имя</th>
                  <th>Роль</th>
                  <th>Дата создания</th>
                  <th>Статус</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(user.id)}
                        onChange={() => toggleSelect(user.id)}
                      />
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.8rem' }}>
                      #{user.id}
                    </td>
                    <td style={{ fontWeight: 500 }}>
                      {user.username}
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {user.email}
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {user.full_name || '—'}
                    </td>
                    <td>
                      <StatusBadge role={user.role} />
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {formatDate(user.created_at)}
                    </td>
                    <td>
                      <span 
                        className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}
                      >
                        {user.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
  */}

  // frontend/src/pages/UsersManagementPage.jsx - ИСПРАВЛЕННЫЙ
  
  import { useState, useEffect } from 'react'
  import { Link, useNavigate } from 'react-router-dom'
  import LoadingSpinner from '../components/LoadingSpinner'
  import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
  import { useAuth } from '../context/AuthContext'
  import Header from '../components/Header'
  import client from '../api/client'
  
  function StatusBadge({ role }) {
    const map = {
      admin: { cls: 'badge-danger', label: 'Admin' },
      analyst: { cls: 'badge-success', label: 'Analyst' },
    }
    const { cls, label } = map[role] ?? { cls: 'badge-secondary', label: role }
    return <span className={`badge ${cls}`}>{label}</span>
  }
  
  function formatDate(dateString) {
    if (!dateString) return '—'
    return new Date(dateString).toLocaleString('ru-RU', { 
      dateStyle: 'short', 
      timeStyle: 'short' 
    })
  }
  
  // ✅ ИСПРАВЛЕНО: Переименована функция (было UsersManagementTab)
  export default function UsersManagementPage() {
    const navigate = useNavigate() 
    const [users, setUsers] = useState([])
    const [selected, setSelected] = useState(new Set())
    const [loading, setLoading] = useState(false)
    const [deleting, setDeleting] = useState(null)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
  
    const fetchUsers = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await client.get('/api/users')
        setUsers(response.data)
        console.log('Users fetched:', response.data)
      } catch (err) {
        console.error('Fetch users error:', err)
        setError(err.response?.data?.detail ?? 'Ошибка при загрузке пользователей')
      } finally {
        setLoading(false)
      }
    }
  
    useEffect(() => { fetchUsers() }, [])
  
    const toggleSelect = (id) => {
      setSelected((prev) => {
        const next = new Set(prev)
        next.has(id) ? next.delete(id) : next.add(id)
        return next
      })
    }
  
    const toggleAll = () => {
      setSelected(
        selected.size === users.length ? new Set() : new Set(users.map((u) => u.id))
      )
    }
  
    const handleDelete = async () => {
      if (!selected.size) return
      if (!window.confirm(`Удалить ${selected.size} пользователей?`)) return
  
      setError('')
      setSuccess('')
      setDeleting(true)
  
      try {
        const userIds = Array.from(selected)
        
        await Promise.all(
          userIds.map((userId) => {
            console.log(`Deleting user ${userId}`)
            return client.delete(`/api/users/${userId}`)
          })
        )
  
        setSuccess(`${selected.size} пользователей удалено`)
        setSelected(new Set())
        fetchUsers()
      } catch (err) {
        console.error('Delete error:', err)
        setError(err.response?.data?.detail ?? 'Ошибка при удалении пользователей')
      } finally {
        setDeleting(false)
      }
    }
  
    return (
      <>
        <Header />
        <main className="page-content">  
          <ErrorMessage message={error} onClose={() => setError('')} />
          <SuccessMessage message={success} onClose={() => setSuccess('')} />
            <button className="back-btn" onClick={() => navigate('/admin')}>
               ← Назад
            </button>
  
          <div className="toolbar">
            {selected.size > 0 && (
              <button 
                className="btn btn-danger" 
                onClick={handleDelete}
                disabled={deleting}
              >
                🗑 Удалить выбранных ({selected.size})
              </button>
            )}
            <button 
              className="btn btn-secondary toolbar-right" 
              onClick={fetchUsers}
              disabled={loading}
            >
              <img src="/icons/icon-refresh.png" alt="refresh" style={{ width: "16px", marginRight: "6px" }} />
              Обновить
            </button>
          </div>
  
          {loading ? (
            <LoadingSpinner text="Загрузка пользователей..." />
          ) : users.length === 0 ? (
            <div className="empty-state card card-body">
              <div style={{ display: "flex", justifyContent: "center" }}>
                <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
              </div>
              <div className="empty-state__text">Нет пользователей в системе.</div>
            </div>
          ) : (
            <div className="card">
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: 40 }}>
                        <input
                          type="checkbox"
                          checked={selected.size === users.length && users.length > 0}
                          onChange={toggleAll}
                        />
                      </th>
                      <th>ID</th>
                      <th>Имя пользователя</th>
                      <th>Email</th>
                      <th>Полное имя</th>
                      <th>Роль</th>
                      <th>Дата создания</th>
                      <th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selected.has(user.id)}
                            onChange={() => toggleSelect(user.id)}
                          />
                        </td>
                        <td style={{ color: 'var(--muted)', fontSize: '.8rem' }}>
                          #{user.id}
                        </td>
                        <td style={{ fontWeight: 500 }}>
                          {user.username}
                        </td>
                        <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                          {user.email}
                        </td>
                        <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                          {user.full_name || '—'}
                        </td>
                        <td>
                          <StatusBadge role={user.role} />
                        </td>
                        <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                          {formatDate(user.created_at)}
                        </td>
                        <td>
                          <span 
                            className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}
                          >
                            {user.is_active ? 'Активен' : 'Неактивен'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </>
    )
  }
  