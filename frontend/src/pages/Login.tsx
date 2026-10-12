import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'

export default function Login({ mode }: { mode: 'login' | 'register' }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const isRegister = mode === 'register'

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (isRegister) await authApi.register(email, password)
      await authApi.login(email, password)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-8 text-slate-100">
      <form onSubmit={onSubmit} className="grid w-full max-w-sm gap-3 rounded-lg border border-slate-800 bg-slate-900 p-6">
        <h1 className="text-xl font-semibold">{isRegister ? 'Create account' : 'Sign in to CodeScope'}</h1>
        <label className="grid gap-1 text-sm">
          Email
          <input type="email" className="rounded bg-slate-800 px-3 py-2" value={email}
                 onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label className="grid gap-1 text-sm">
          Password {isRegister && <span className="text-xs text-slate-500">(at least 8 characters)</span>}
          <input type="password" className="rounded bg-slate-800 px-3 py-2" value={password}
                 onChange={(e) => setPassword(e.target.value)} required minLength={isRegister ? 8 : 1}
                 autoComplete={isRegister ? 'new-password' : 'current-password'} />
        </label>
        {error && (
          <div role="alert" className="rounded border border-red-800 bg-red-950 p-2 text-sm text-red-200">{error}</div>
        )}
        <button type="submit" disabled={busy} className="rounded bg-indigo-600 px-4 py-2 font-medium disabled:opacity-50">
          {busy ? 'Please wait...' : isRegister ? 'Register' : 'Sign in'}
        </button>
        <Link to={isRegister ? '/login' : '/register'} className="text-sm text-indigo-300 hover:underline">
          {isRegister ? 'Already have an account? Sign in' : 'No account? Register'}
        </Link>
      </form>
    </div>
  )
}