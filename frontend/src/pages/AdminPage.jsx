// frontend/src/pages/AdminPage.jsx

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Header from '../components/Header'

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

const TABS = ['users', 'models']
const TAB_LABELS = { 
  users: 'Управление пользователями'
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [activeTab, setActiveTab] = useState('users')

  return (
    <>
      <Header />
      <main className="page-content">
        <div className="page-title">Администрирование</div>
        <div className="page-subtitle">Управление системой и пользователями</div>

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

        {activeTab === 'users' && (
          <div>
            <p className="page-subtitle">
              Управление пользователями системы.
            </p>
            <div className="nav-cards">
              <NavTab
                title="Просмотр и управление пользователями"
                desc="Просмотрите список всех пользователей и управляйте ими"
                onClick={() => navigate('/admin/users/management')}
              />
              <NavTab
                title="Добавить пользователя"
                desc="Создайте новый аккаунт пользователя"
                onClick={() => navigate('/admin/users/add')}
              />
            </div>
          </div>
        )}
      </main>
    </>
  )
}