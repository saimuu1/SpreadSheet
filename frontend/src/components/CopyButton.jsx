import { useState } from 'react'
import { IconCopy, IconCheck } from './icons'

export default function CopyButton({ text, label = 'Copy', className = '' }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Fallback for non-secure contexts
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-white/25 hover:text-white ${className}`}
    >
      {copied ? <IconCheck width={14} height={14} className="text-emerald-400" /> : <IconCopy width={14} height={14} />}
      {copied ? 'Copied' : label}
    </button>
  )
}
