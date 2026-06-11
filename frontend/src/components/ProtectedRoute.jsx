import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { IconSpinner } from './icons'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        <IconSpinner width={28} height={28} />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}
