import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LoginPage        from './pages/LoginPage'
import ProtectedRoute from './components/ProtectedRoute'
import AddUserPage from './pages/AddUserPage'
import AddModelPage from './pages/AddModelPage'
import DashboardPage    from './pages/DashboardPage'
import DecompositionPage from './pages/DecompositionPage'
import ForecastPage     from './pages/ForecastPage'
import AdminPage from './pages/AdminPage' 
import UsersManagementPage from './pages/UsersManagementPage'          


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
       <Route path="/login" element={<LoginPage />} />

        <Route path="/dashboard" element={
          <ProtectedRoute><DashboardPage /></ProtectedRoute>
        } />

        <Route path="/decomposition" element={
          <ProtectedRoute><DecompositionPage /></ProtectedRoute>
        } />

        <Route path="/forecast" element={
          <ProtectedRoute><ForecastPage /></ProtectedRoute>
        } />

        {/* Администрирование */}
        <Route path="/admin" element={
          <ProtectedRoute requiredRole="admin">
            <AdminPage />
          </ProtectedRoute>
        } />

        <Route path="admin/users/add" element={
        <ProtectedRoute requiredRole="admin">
          <AddUserPage />
        </ProtectedRoute>
      } />

      <Route path="/admin/users/management" element={
          <ProtectedRoute requiredRole="admin">
            <UsersManagementPage />
          </ProtectedRoute>
        } />
      
      <Route path="admin/models/add" element={
        <ProtectedRoute requiredRole="admin">
          <AddModelPage />
        </ProtectedRoute>
      } />

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
