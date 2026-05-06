// frontend/src/context/AuthContext.js
/**
 * AuthContext с поддержкой ролей (admin, analyst)
 * Хранит: token, userId, username, role
 */

import { createContext, useContext, useState, useCallback } from 'react'
import client from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // ✅ ДОБАВЛЕНЫ: role
  const [token,    setToken]    = useState(() => localStorage.getItem('token')    || null)
  const [userId,   setUserId]   = useState(() => localStorage.getItem('user_id')  || null)
  const [username, setUsername] = useState(() => localStorage.getItem('username') || null)
  const [role,     setRole]     = useState(() => localStorage.getItem('role')     || null) 

  const login = useCallback(async (usernameVal, password) => {
    // FastAPI OAuth2 json
    const { data } = await client.post('/api/auth/login', 
      {
        username: usernameVal,
        password: password
      },
      {
        headers: { 'Content-Type': 'application/json' }
      }
    )

    const tok = data.access_token
    const uid = String(data.user_id ?? 1)
    const uname = data.username ?? usernameVal
    const r = data.role ?? 'analyst'  

    // Сохранить в localStorage
    localStorage.setItem('token',    tok)
    localStorage.setItem('user_id',  uid)
    localStorage.setItem('username', uname)
    localStorage.setItem('role',     r)  

    // Обновить состояние
    setToken(tok)
    setUserId(uid)
    setUsername(uname)
    setRole(r)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')
    localStorage.removeItem('role') 

    setToken(null)
    setUserId(null)
    setUsername(null)
    setRole(null) 
  }, [])
    console.log("AuthContext loaded:", !!window.__react__);
    console.log("localStorage keys:", Object.keys(localStorage));
  return (
    <AuthContext.Provider value={{ 
      token, 
      userId, 
      username, 
      role, 
      login, 
      logout, 
      isAuth: !!token,
      isAdmin: role === 'admin', 
      isAnalyst: role === 'analyst', 
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth должен использоваться внутри AuthProvider')
  }
  return context
}