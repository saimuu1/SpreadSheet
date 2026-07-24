import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="mt-32 border-t border-white/5 py-10">
      <div className="container-page flex flex-col items-center justify-between gap-4 text-sm text-slate-500 sm:flex-row">
        <Logo />
        <p>© {new Date().getFullYear()} Sheetwave</p>
      </div>
    </footer>
  )
}
