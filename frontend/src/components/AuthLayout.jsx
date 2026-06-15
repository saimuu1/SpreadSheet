import { Link } from 'react-router-dom'
import Logo from './Logo'
import { IconBolt, IconShield, IconCode } from './icons'

const points = [
  { icon: IconBolt, text: 'Live REST API the moment you upload' },
  { icon: IconCode, text: 'Filter, sort & paginate right in the URL' },
  { icon: IconShield, text: 'Hashed API keys & row-level security' },
]

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand / marketing panel */}
      <div className="flex flex-col justify-between border-r border-white/[0.08] bg-white/[0.01] p-12 lg:flex hidden">
        <Logo />
        <div>
          <h2 className="max-w-md text-3xl font-bold leading-tight text-white">
            Turn any spreadsheet into a <span className="text-accent">production API</span> in seconds.
          </h2>
          <ul className="mt-8 space-y-4">
            {points.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-slate-300">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-brand-400">
                  <Icon width={18} height={18} />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-slate-500">Upload → infer schema → query. No backend code.</p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-slate-400">{footer}</div>}
          <p className="mt-10 text-center text-xs text-slate-600">
            <Link to="/" className="hover:text-slate-400">← Back to home</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
