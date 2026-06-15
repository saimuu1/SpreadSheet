import { Link } from 'react-router-dom'

export default function Logo({ to = '/' }) {
  return (
    <Link to={to} className="group flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 7h18M3 12h18M3 17h18M8 3v18" />
        </svg>
      </span>
      <span className="text-[17px] font-bold tracking-tight text-white">
        Sheet<span className="text-brand-400">wave</span>
      </span>
    </Link>
  )
}
