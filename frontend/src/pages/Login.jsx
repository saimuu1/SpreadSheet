import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AuthLayout from '../components/AuthLayout'
import { IconSpinner, IconArrowRight } from '../components/icons'

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const { error } = await signIn(email, password)
    setLoading(false)
    if (error) return setError(error.message)
    navigate('/dashboard')
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to manage your datasets and API keys."
      footer={
        <>
          New here?{' '}
          <Link to="/signup" className="font-semibold text-brand-300 hover:text-brand-200">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)} className="input" placeholder="you@example.com" />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input id="password" type="password" required value={password}
            onChange={(e) => setPassword(e.target.value)} className="input" placeholder="••••••••" />
        </div>
        {error && (
          <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>
        )}
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? <IconSpinner width={16} height={16} /> : <>Log in <IconArrowRight width={16} height={16} /></>}
        </button>
      </form>
    </AuthLayout>
  )
}
