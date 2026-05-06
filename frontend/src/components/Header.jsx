{/*
import { useAuth } from '../context/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

export default function Header() {
  const { username, role, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="app-header__logo">
          <img src="/icons/main_icon.png" alt="Logo" style={{ width: '30px' }} />
          <span>БюджетПрогноз</span>
        </div>
        {isAdmin && (
          <nav className="app-header__admin-nav" style={{ display: 'flex', gap: '1rem' }}>
            <Link 
              to="/users/add" 
              className="btn btn-primary btn-sm"
              style={{ textDecoration: 'none' }}
            >
              ➕ Добавить пользователя
            </Link>
            <Link 
              to="/models/add" 
              className="btn btn-primary btn-sm"
              style={{ textDecoration: 'none' }}
            >
              ➕ Добавить модель
            </Link>
          </nav>
        )}

        <div className="app-header__user">
          {username && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              Привет, <strong>{username}</strong>!
              <span 
                style={{ 
                  fontSize: '0.75rem', 
                  color: 'var(--muted)',
                  padding: '0.2rem 0.5rem',
                  backgroundColor: isAdmin ? '#ffe8e8' : '#e8f5e9',
                  borderRadius: '4px',
                }}
              >
                {isAdmin ? '👑 Admin' : '👤 Analyst'}
              </span>
            </span>
          )}
          <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
            Выход
          </button>
        </div>
      </div>
    </header>
  )
}

*/}

// frontend/src/components/Header.jsx

import { useAuth } from '../context/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

export default function Header() {
  const { username, role, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="app-header__logo">
          <img src="/icons/main_icon.png" alt="Logo" style={{ width: '30px' }} />
          <span>БюджетПрогноз</span>
        </div>

        {/* Навигация */}
        <nav className="app-header__nav" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          
          {isAdmin && (
            <Link 
              to="/admin" 
              className="btn btn-primary btn-sm"
              style={{ textDecoration: 'none' }}
            >
              Администрирование
            </Link>
          )
        }
          { isAdmin && (
            <Link 
            to="/dashboard" 
            className="btn btn-secondary btn-sm"
            style={{ textDecoration: 'none' }}
          >
            Главная
          </Link>
          )
          }
        </nav>

        <div className="app-header__user">
          {username && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              Привет, <strong>{username}</strong>!
              <span 
                style={{ 
                  fontSize: '0.75rem', 
                  color: 'var(--muted)',
                  padding: '0.2rem 0.5rem',
                  backgroundColor: isAdmin ? '#ffe8e8' : '#e8f5e9',
                  borderRadius: '4px',
                }}
              >
                {isAdmin ? 'Admin' : 'Analyst'}
              </span>
            </span>
          )}
          <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
            Выход
          </button>
        </div>
      </div>
    </header>
  )
}