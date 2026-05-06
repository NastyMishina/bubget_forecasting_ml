{/* 
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import Modal from '../components/Modal'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
import client from '../api/client'

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmtSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1048576)    return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}

function StatusBadge({ status }) {
  const map = {
    validated:  { cls: 'badge-success',   label: 'Проверен' },
    completed:  { cls: 'badge-success',   label: 'Готов' },
    pending:    { cls: 'badge-warning',   label: 'Ожидание' },
    validating: { cls: 'badge-warning',   label: 'Проверка' },
    failed:     { cls: 'badge-danger',    label: 'Ошибка' },
  }
  const { cls, label } = map[status] ?? { cls: 'badge-secondary', label: status ?? '—' }
  return <span className={`badge ${cls}`}>{label}</span>
}

// ─── Upload modal ─────────────────────────────────────────────────────────────

function UploadModal({ onClose, onSuccess }) {
  const fileRef  = useRef(null)
  const [file,    setFile]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleUpload = async () => {
    if (!file) { setError('Выберите файл'); return }
    if (!file.name.match(/\.(csv|xlsx)$/i)) { setError('Разрешены только .csv и .xlsx'); return }

    setLoading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      await client.post('/api/data/upload', fd)
      onSuccess('Файл успешно загружен')
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при загрузке файла')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="Загрузить файл"
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary"   onClick={handleUpload} disabled={loading}>
            {loading ? 'Загрузка...' : 'Загрузить'}
          </button>
        </>
      }
    >
      <ErrorMessage message={error} onClose={() => setError('')} />

      <label className="file-drop">
        <input 
          ref={fileRef} 
          type="file" 
          accept=".csv,.xlsx" 
          onChange={(e) => setFile(e.target.files[0])}
          style={{ display: 'none' }}
        />
        <div style={{ display: "flex", justifyContent: "center" }}>
          <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
        </div>
        <div>Нажмите для выбора файла</div>
        <div style={{ fontSize: '.78rem', color: 'var(--muted)', marginTop: '.25rem' }}>
          Поддерживаются: .csv, .xlsx
        </div>
        {file && <div className="file-drop__name">{file.name}</div>}
      </label>
    </Modal>
  )
}

// ─── Uploads Tab ─────────────────────────────────────────────────────────────

function UploadsTab() {
  const { userId } = useAuth()
   console.log('userId =', userId)
  const [uploads,     setUploads]     = useState([])
  const [selected,    setSelected]    = useState(new Set())
  const [loading,     setLoading]     = useState(false)
  const [processing,  setProcessing]  = useState(null)   // upload_id being processed
  const [showModal,   setShowModal]   = useState(false)
  const [error,       setError]       = useState('')
  const [success,     setSuccess]     = useState('')

  const fetchUploads = async () => {
    console.log('fetchUploads: НАЧАЛО, userId =', userId)
    setLoading(true); setError('')
    try {
      const url = `/api/data/uploads/${userId}`
      console.log('fetchUploads: отправляю запрос на URL =', url)

      const response = await client.get(url)
      console.log('fetchUploads: ответ получен =', response)
      console.log('fetchUploads: response.data =', response.data)

      const { data } = response
      console.log('fetchUploads: data =', data)

      const uploadsList = Array.isArray(data) ? data : (data.uploads || [])
      console.log('fetchUploads: uploadsList =', uploadsList)
      setUploads(uploadsList)
      console.log('fetchUploads: setUploads вызван')

    } catch (err) {
      setError(err.response?.data?.detail ?? 'Не удалось загрузить список файлов')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUploads() }, []) 

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected(selected.size === uploads.length ? new Set() : new Set(uploads.map((u) => u.id)))
  }

  const handleProcess = async (uploadId) => {
    setProcessing(uploadId); setError(''); setSuccess('')
    try {
      await client.post(`/api/data/process/${uploadId}`)
      setSuccess(`Признаки успешно созданы для загрузки #${uploadId}`)
      fetchUploads()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при создании признаков')
    } finally {
      setProcessing(null)
    }
  }

  const handleDelete = async () => {
    if (!selected.size) return
    if (!window.confirm(`Удалить ${selected.size} файл(ов)?`)) return
    setError(''); setSuccess('')
    try {
      await Promise.all([...selected].map((id) => client.delete(`/api/uploads/${id}`)))
      setSuccess('Файлы удалены')
      setSelected(new Set())
      fetchUploads()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при удалении')
    }
  }

  return (
    <div>
      <ErrorMessage   message={error}   onClose={() => setError('')} />
      <SuccessMessage message={success} onClose={() => setSuccess('')} />

      <div className="toolbar">
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Загрузить файл
        </button>
        {selected.size > 0 && (
          <button className="btn btn-danger" onClick={handleDelete}>
            🗑 Удалить выбранные ({selected.size})
          </button>
        )}
        <button className="btn btn-secondary toolbar-right" onClick={fetchUploads}>
           <img src="/icons/icon-refresh.png" alt="refresh" style={{ width: "16px", marginRight: "6px" }}/> 
           Обновить
        </button>
      </div>

      {loading ? (
        <LoadingSpinner text="Загрузка файлов..." />
      ) : uploads.length === 0 ? (
        <div className="empty-state card card-body">
          <div style={{ display: "flex", justifyContent: "center" }}>
             <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
          </div>
          <div className="empty-state__text">Загрузок пока нет. Загрузите первый файл.</div>
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
                      checked={selected.size === uploads.length && uploads.length > 0}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>ID</th>
                  <th>Файл</th>
                  <th>Дата</th>
                  <th>Размер</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(u.id)}
                        onChange={() => toggleSelect(u.id)}
                      />
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.8rem' }}>#{u.id}</td>
                    <td>
                      <span title={u.file_path} style={{ fontWeight: 500 }}>
                        {u.filename}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {fmtDate(u.created_at || u.upload_date)}
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {fmtSize(u.file_size)}
                    </td>
                    <td><StatusBadge status={u.status} /></td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleProcess(u.id)}
                        disabled={processing === u.id}
                        title="Создать признаки для обучения"
                      >
                        {processing === u.id ? '...' : 'Признаки'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showModal && (
        <UploadModal
          onClose={() => setShowModal(false)}
          onSuccess={(msg) => { setSuccess(msg); fetchUploads() }}
        />
      )}
    </div>
  )
}

// Вкладки Загрузка 

function NavTab({ icon, title, desc, onClick }) {
  return (
    <div className="nav-card" onClick={onClick}>
      <div className="nav-card__icon">{icon}</div>
      <div className="nav-card__title">{title}</div>
      <div className="nav-card__desc">{desc}</div>
      <div style={{ marginTop: 'auto' }}>
        <span className="btn btn-primary btn-sm">Перейти</span>
      </div>
    </div>
  )
}

// Dashboard Page

const TABS = ['uploads', 'decomposition', 'forecast']
const TAB_LABELS = { uploads: 'Загрузки', decomposition: 'Декомпозиция', forecast: 'Прогноз' }

export default function DashboardPage() {
  const navigate   = useNavigate()
  const [activeTab, setActiveTab] = useState('uploads')

  return (
    <>
      <Header />
      <main className="page-content">
        <div className="page-title">Главная</div>
        <div className="page-subtitle">Управление данными и прогнозами</div>

        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              className={`tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {activeTab === 'uploads' && <UploadsTab />}

        {activeTab === 'decomposition' && (
          <div>
            <p className="page-subtitle">
              Анализ сезонности и трендов временных рядов ваших данных.
            </p>
            <div className="nav-cards">
              <NavTab
                icon=""
                title="Декомпозиция временных рядов"
                onClick={() => navigate('/decomposition')}
              />
            </div>
          </div>
        )}

        {activeTab === 'forecast' && (
          <div>
            <p className="page-subtitle">
              Запустите прогнозирование с помощью предобученных ML-моделей.
            </p>
            <div className="nav-cards">
              <NavTab
                icon=""
                title="Прогнозирование бюджета"
                onClick={() => navigate('/forecast')}
              />
            </div>
          </div>
        )}
      </main>
    </>
  )
}
*/}


import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'
import Modal from '../components/Modal'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage, { SuccessMessage } from '../components/ErrorMessage'
import client from '../api/client'

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmtSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024)       return `${bytes} B`
  if (bytes < 1048576)    return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}

function StatusBadge({ status }) {
  const map = {
    validated:  { cls: 'badge-success',   label: 'Проверен' },
    completed:  { cls: 'badge-success',   label: 'Готов' },
    pending:    { cls: 'badge-warning',   label: 'Ожидание' },
    validating: { cls: 'badge-warning',   label: 'Проверка' },
    failed:     { cls: 'badge-danger',    label: 'Ошибка' },
  }
  const { cls, label } = map[status] ?? { cls: 'badge-secondary', label: status ?? '—' }
  return <span className={`badge ${cls}`}>{label}</span>
}

// ─── Upload modal ─────────────────────────────────────────────────────────────

function UploadModal({ onClose, onSuccess }) {
  const { userId } = useAuth()
  const fileRef  = useRef(null)
  const [file,    setFile]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleUpload = async () => {
    if (!file) { setError('Выберите файл'); return }
    if (!file.name.match(/\.(csv|xlsx)$/i)) { setError('Разрешены только .csv и .xlsx'); return }

    setLoading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      await client.post('/api/data/upload', fd)
      onSuccess('Файл успешно загружен')
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при загрузке файла')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title="Загрузить файл"
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary"   onClick={handleUpload} disabled={loading}>
            {loading ? 'Загрузка...' : 'Загрузить'}
          </button>
        </>
      }
    >
      <ErrorMessage message={error} onClose={() => setError('')} />

      <label className="file-drop">
        <input 
          ref={fileRef} 
          type="file" 
          accept=".csv,.xlsx" 
          onChange={(e) => setFile(e.target.files[0])}
          style={{ display: 'none' }}
        />
        <div style={{ display: "flex", justifyContent: "center" }}>
          <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
        </div>
        <div>Нажмите для выбора файла</div>
        <div style={{ fontSize: '.78rem', color: 'var(--muted)', marginTop: '.25rem' }}>
          Поддерживаются: .csv, .xlsx
        </div>
        {file && <div className="file-drop__name">{file.name}</div>}
      </label>
    </Modal>
  )
}

// ─── Uploads Tab ─────────────────────────────────────────────────────────────

function UploadsTab() {
  const { userId, isAdmin } = useAuth()
  const [uploads,     setUploads]     = useState([])
  const [selected,    setSelected]    = useState(new Set())
  const [loading,     setLoading]     = useState(false)
  const [processing,  setProcessing]  = useState(null) 
  const [showModal,   setShowModal]   = useState(false)
  const [error,       setError]       = useState('')
  const [success,     setSuccess]     = useState('')

  const fetchUploads = async () => {
    setLoading(true); 
    setError('')
    try {
      const url = isAdmin ? '/api/data/uploads' : `/api/data/uploads/${userId}`
      
      const response = await client.get(url)
      const { data } = response

      const uploadsList = Array.isArray(data) ? data : (data.uploads || [])
      setUploads(uploadsList)

    } catch (err) {
      setError(err.response?.data?.detail ?? 'Не удалось загрузить список файлов')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchUploads() }, [isAdmin, userId]) 

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    setSelected(selected.size === uploads.length ? new Set() : new Set(uploads.map((u) => u.id)))
  }

  const handleProcess = async (uploadId) => {
    setProcessing(uploadId); setError(''); setSuccess('')
    try {
      await client.post(`/api/data/process/${uploadId}`)
      setSuccess(`Признаки успешно созданы для загрузки #${uploadId}`)
      fetchUploads()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Ошибка при создании признаков')
    } finally {
      setProcessing(null)
    }
  }

  {/*const handleDelete = async () => {
    if (!selected.size) return
    if (!window.confirm(`Удалить ${selected.size} файл(ов)?`)) return
    setError(''); setSuccess('')
    try {
      console.log('Deleting uploads:', [...selected])
      await Promise.all([...selected].map((id) => client.delete(`/api/data/uploads/${id}`)))
      console.log(`Sending DELETE request for upload ${id}`)
      setSuccess('Файлы удалены')
      setSelected(new Set())
      fetchUploads()
    } catch (err) {
      console.error('Delete error:', err)
      setError(err.response?.data?.detail ?? 'Ошибка при удалении')
    }
  }*/}
  const handleDelete = async () => {
  if (!selected.size) return
  if (!window.confirm(`Удалить ${selected.size} файл(ов)?`)) return
  setError('')
  setSuccess('')
  
  try {
    console.log('Deleting uploads:', [...selected])
    
    // Создаем массив ID для удаления
    const uploadIds = Array.from(selected)
    
    // Удаляем каждый файл
    await Promise.all(
      uploadIds.map((uploadId) => {
        console.log(`Sending DELETE request for upload ${uploadId}`)
        return client.delete(`/api/data/uploads/${uploadId}`)
      })
    )
    
    console.log('All uploads deleted successfully')
    setSuccess('Файлы удалены')
    setSelected(new Set())
    
    // Обновляем список
    await fetchUploads()
    
  } catch (err) {
    console.error('Delete error details:', {
      status: err.response?.status,
      statusText: err.response?.statusText,
      data: err.response?.data,
      message: err.message,
      stack: err.stack
    })
    setError(err.response?.data?.detail ?? err.message ?? 'Ошибка при удалении')
  }
}

  return (
    <div>
      <ErrorMessage   message={error}   onClose={() => setError('')} />
      <SuccessMessage message={success} onClose={() => setSuccess('')} />

      <div className="toolbar">
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          + Загрузить файл
        </button>
        {selected.size > 0 && (
          <button className="btn btn-danger" onClick={handleDelete}>
            🗑 Удалить выбранные ({selected.size})
          </button>
        )}
        <button className="btn btn-secondary toolbar-right" onClick={fetchUploads}>
           <img src="/icons/icon-refresh.png" alt="refresh" style={{ width: "16px", marginRight: "6px" }}/> 
           Обновить
        </button>
      </div>

      {}
      {isAdmin && uploads.length > 0 && (
        <div style={{ 
          marginBottom: '1rem', 
          padding: '0.75rem', 
          backgroundColor: '#e3f2fd',
          borderRadius: '4px',
          fontSize: '0.9rem'
        }}>
        </div>
      )}

      {loading ? (
        <LoadingSpinner text="Загрузка файлов..." />
      ) : uploads.length === 0 ? (
        <div className="empty-state card card-body">
          <div style={{ display: "flex", justifyContent: "center" }}>
             <img src="/icons/icon-folder.png" alt="Logo" style={{ width: "30px" }} />
          </div>
          <div className="empty-state__text">
            {isAdmin ? 'Нет загрузок от пользователей' : 'Загрузок пока нет. Загрузите первый файл.'}
          </div>
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
                      checked={selected.size === uploads.length && uploads.length > 0}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>ID</th>
                  {isAdmin && <th>Пользователь</th>}
                  <th>Файл</th>
                  <th>Дата</th>
                  <th>Размер</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(u.id)}
                        onChange={() => toggleSelect(u.id)}
                      />
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.8rem' }}>#{u.id}</td>
                    {isAdmin && (
                      <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                        {u.user?.username || u.user_id || '—'}
                      </td>
                    )}
                    <td>
                      <span title={u.file_path} style={{ fontWeight: 500 }}>
                        {u.filename}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {fmtDate(u.created_at || u.upload_date)}
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: '.82rem' }}>
                      {fmtSize(u.file_size)}
                    </td>
                    <td><StatusBadge status={u.status} /></td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleProcess(u.id)}
                        disabled={processing === u.id}
                        title="Создать признаки для обучения"
                      >
                        {processing === u.id ? '...' : 'Признаки'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showModal && (
        <UploadModal
          onClose={() => setShowModal(false)}
          onSuccess={(msg) => { setSuccess(msg); fetchUploads() }}
        />
      )}
    </div>
  )
}

// Вкладки Загрузка 

function NavTab({ icon, title, desc, onClick }) {
  return (
    <div className="nav-card" onClick={onClick}>
      <div className="nav-card__icon">{icon}</div>
      <div className="nav-card__title">{title}</div>
      <div className="nav-card__desc">{desc}</div>
      <div style={{ marginTop: 'auto' }}>
        <span className="btn btn-primary btn-sm">Перейти</span>
      </div>
    </div>
  )
}

// Dashboard Page

const TABS = ['uploads', 'decomposition', 'forecast']
const TAB_LABELS = { uploads: 'Загрузки', decomposition: 'Декомпозиция', forecast: 'Прогноз' }

export default function DashboardPage() {
  const navigate   = useNavigate()
  const [activeTab, setActiveTab] = useState('uploads')

  return (
    <>
      <Header />
      <main className="page-content">
        <div className="page-title">Главная</div>
        <div className="page-subtitle">Управление данными и прогнозами</div>

        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab}
              className={`tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {activeTab === 'uploads' && <UploadsTab />}

        {activeTab === 'decomposition' && (
          <div>
            <p className="page-subtitle">
              Анализ сезонности и трендов временных рядов ваших данных.
            </p>
            <div className="nav-cards">
              <NavTab
                icon=""
                title="Декомпозиция временных рядов"
                onClick={() => navigate('/decomposition')}
              />
            </div>
          </div>
        )}

        {activeTab === 'forecast' && (
          <div>
            <p className="page-subtitle">
              Запустите прогнозирование с помощью предобученных ML-моделей.
            </p>
            <div className="nav-cards">
              <NavTab
                icon=""
                title="Прогнозирование коммерческих расходов"
                onClick={() => navigate('/forecast')}
              />
            </div>
          </div>
        )}
      </main>
    </>
  )
}