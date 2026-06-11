import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'
import { IconArrowRight, IconLogout } from './icons'

export default function Navbar() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const onLanding = location.pathname === '/'

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-ink/70 backdrop-blur-xl">
      <div className="container-page flex h-16 items-center justify-between">
        <Logo />

        {onLanding && (
          <nav className="hidden items-center gap-8 text-sm text-slate-300 md:flex">
            <a href="#how" className="transition hover:text-white">How it works</a>
            <a href="#features" className="transition hover:text-white">Features</a>
            <a href="#pricing" className="transition hover:text-white">Pricing</a>
          </nav>
        )}

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <Link to="/dashboard" className="btn-subtle">Dashboard</Link>
              <button onClick={handleSignOut} className="btn-ghost">
                <IconLogout width={16} height={16} /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-subtle">Log in</Link>
              <Link to="/signup" className="btn-primary">
                Get started <IconArrowRight width={16} height={16} />
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
