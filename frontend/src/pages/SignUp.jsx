import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AuthLayout from '../components/AuthLayout'
import { IconSpinner, IconArrowRight, IconCheck } from '../components/icons'

export default function SignUp() {
  const { signUp, signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [needsConfirm, setNeedsConfirm] = useState(false)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const { data, error } = await signUp(email, password)
    if (error) {
      setLoading(false)
      return setError(error.message)
    }
    // If the project has email confirmation off, a session is returned (or sign-in works).
    if (data.session) {
      setLoading(false)
      return navigate('/dashboard')
    }
    const { error: signInError } = await signIn(email, password)
    setLoading(false)
    if (!signInError) return navigate('/dashboard')
    setNeedsConfirm(true)
  }

  if (needsConfirm) {
    return (
      <AuthLayout title="Almost there" subtitle="Your account was created.">
        <div className="card flex items-start gap-3 p-5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <IconCheck width={18} height={18} />
          </span>
          <div className="text-sm text-slate-300">
            <p className="font-medium text-white">Confirm your email</p>
            <p className="mt-1 text-slate-400">
              We sent a confirmation link to <span className="text-slate-200">{email}</span>. Click it, then log in.
            </p>
            <Link to="/login" className="btn-primary mt-4 w-full">Go to login</Link>
          </div>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start turning spreadsheets into APIs — free."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-brand-300 hover:text-brand-200">Log in</Link>
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
          <input id="password" type="password" required minLength={6} value={password}
            onChange={(e) => setPassword(e.target.value)} className="input" placeholder="At least 6 characters" />
        </div>
        {error && (
          <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>
        )}
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? <IconSpinner width={16} height={16} /> : <>Create account <IconArrowRight width={16} height={16} /></>}
        </button>
      </form>
    </AuthLayout>
  )
}
