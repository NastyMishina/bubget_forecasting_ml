// frontend/src/components/ProtectedRoute.jsx
/**
 * ProtectedRoute компонент для защиты маршрутов по ролям
 * 
 * Использование:
 * <Route path="/admin/users" element={
 *   <ProtectedRoute requiredRole="admin">
 *     <AddUserPage />
 *   </ProtectedRoute>
 * } />
 */

import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children, requiredRole = null }) {
  const { isAuth, role } = useAuth()

  if (!isAuth) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && role !== requiredRole && role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return children
}