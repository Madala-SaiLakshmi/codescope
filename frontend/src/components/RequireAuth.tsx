import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { getToken } from '../services/auth'

export default function RequireAuth({ children }: { children: ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />
}