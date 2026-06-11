const STYLES = {
  number: 'bg-accent-500/15 text-accent-300',
  text: 'bg-brand-500/15 text-brand-300',
  boolean: 'bg-emerald-500/15 text-emerald-300',
  date: 'bg-amber-500/15 text-amber-300',
}

export default function TypePill({ type }) {
  return <span className={`pill-type ${STYLES[type] || STYLES.text}`}>{type}</span>
}
