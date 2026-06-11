// Lightweight inline icon set (stroke-based, inherits currentColor).
const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

export const IconBolt = (p) => (
  <svg {...base} {...p}><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z" /></svg>
)
export const IconUpload = (p) => (
  <svg {...base} {...p}><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M5 20h14" /></svg>
)
export const IconKey = (p) => (
  <svg {...base} {...p}><circle cx="8" cy="15" r="4" /><path d="m11 12 8-8m-3 0 3 3m-5 2 2 2" /></svg>
)
export const IconDatabase = (p) => (
  <svg {...base} {...p}><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></svg>
)
export const IconCode = (p) => (
  <svg {...base} {...p}><path d="m16 18 6-6-6-6M8 6l-6 6 6 6" /></svg>
)
export const IconCheck = (p) => (
  <svg {...base} {...p}><path d="M20 6 9 17l-5-5" /></svg>
)
export const IconCopy = (p) => (
  <svg {...base} {...p}><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
)
export const IconArrowRight = (p) => (
  <svg {...base} {...p}><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
)
export const IconLogout = (p) => (
  <svg {...base} {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5M21 12H9" /></svg>
)
export const IconTrash = (p) => (
  <svg {...base} {...p}><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /></svg>
)
export const IconPlus = (p) => (
  <svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>
)
export const IconSparkle = (p) => (
  <svg {...base} {...p}><path d="M12 3v4m0 10v4M3 12h4m10 0h4M5.6 5.6l2.8 2.8m7.2 7.2 2.8 2.8m0-12.8-2.8 2.8M8.4 15.6l-2.8 2.8" /></svg>
)
export const IconShield = (p) => (
  <svg {...base} {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></svg>
)
export const IconGauge = (p) => (
  <svg {...base} {...p}><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" /><path d="m13.4 11.6 3.6-3.6" /><path d="M4 18a8 8 0 1 1 16 0" /></svg>
)
export const IconLayers = (p) => (
  <svg {...base} {...p}><path d="m12 2 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 17l9 5 9-5" /></svg>
)
export const IconSpinner = (p) => (
  <svg {...base} {...p} className={`animate-spin ${p?.className || ''}`}><path d="M21 12a9 9 0 1 1-6.2-8.5" /></svg>
)
