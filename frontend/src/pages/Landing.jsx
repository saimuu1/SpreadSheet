import { Link } from 'react-router-dom'
import Footer from '../components/Footer'
import {
  IconArrowRight, IconUpload, IconLayers, IconCode, IconBolt,
  IconShield, IconGauge, IconDatabase, IconCheck, IconSparkle,
} from '../components/icons'

function ApiDemo() {
  return (
    <div className="card animate-fade-up delay-2 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
        <span className="h-3 w-3 rounded-full bg-red-400/70" />
        <span className="h-3 w-3 rounded-full bg-yellow-400/70" />
        <span className="h-3 w-3 rounded-full bg-green-400/70" />
        <span className="ml-3 font-mono text-xs text-slate-500">products.api</span>
      </div>
      <div className="space-y-3 p-5 font-mono text-[13px] leading-relaxed">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-emerald-300">GET</span>
          <span className="text-slate-300">/api/v1/datasets/<span className="text-slate-500">…</span></span>
        </div>
        <div className="text-slate-400">
          ?category=<span className="text-brand-300">protein</span>
          &amp;price__gt=<span className="text-accent-400">20</span>
          &amp;sort=<span className="text-accent-400">-rating</span>
        </div>
        <div className="rounded-xl border border-white/5 bg-black/30 p-4 text-slate-300">
          <div><span className="text-slate-500">{'{'}</span></div>
          <div className="pl-4"><span className="text-brand-300">"data"</span>: [</div>
          <div className="pl-8 text-slate-400">{'{ '}<span className="text-brand-300">"name"</span>: <span className="text-emerald-300">"Creatine"</span>, <span className="text-brand-300">"price"</span>: <span className="text-accent-400">24.99</span>, <span className="text-brand-300">"rating"</span>: <span className="text-accent-400">4.8</span> {'}'}</div>
          <div className="pl-4">],</div>
          <div className="pl-4"><span className="text-brand-300">"page"</span>: <span className="text-accent-400">1</span>, <span className="text-brand-300">"total"</span>: <span className="text-accent-400">1</span></div>
          <div><span className="text-slate-500">{'}'}</span></div>
        </div>
      </div>
    </div>
  )
}

const steps = [
  { icon: IconUpload, title: 'Upload a CSV', body: 'Drag in any spreadsheet. No schema setup, no migrations.' },
  { icon: IconLayers, title: 'We infer the schema', body: 'Each column is typed automatically — number, boolean, date or text.' },
  { icon: IconCode, title: 'Query the live API', body: 'Filter, sort and paginate with a clean URL syntax. JSON out.' },
]

const features = [
  { icon: IconBolt, title: 'Instant REST endpoints', body: 'A queryable API exists the second your upload finishes.' },
  { icon: IconCode, title: 'A real query language', body: 'price__gt=20, name__contains=oil, sort=-rating, pagination — all in the URL.' },
  { icon: IconShield, title: 'Secure by design', body: 'Hashed API keys, schema-whitelisted fields, parameterized queries, Postgres RLS.' },
  { icon: IconGauge, title: 'Rate limits & tiers', body: 'Per-plan request caps enforced in the backend, not faked in the UI.' },
  { icon: IconDatabase, title: 'Any shape of data', body: 'Stored as jsonb, so every file just works — no table gymnastics.' },
  { icon: IconSparkle, title: 'Auto-generated docs', body: 'Every dataset gets its own docs page with fields, operators and examples.' },
]

const tiers = [
  {
    name: 'Free', price: '$0', blurb: 'Everything to build and test.',
    features: ['1 dataset', '1,000 requests / day', '10 requests / min', 'Full query language'],
    cta: 'Start free', highlight: false,
  },
  {
    name: 'Pro', price: '$7', per: '/mo', blurb: 'For real, growing workloads.',
    features: ['Unlimited datasets', '100,000 requests / day', '120 requests / min', 'Private key-protected APIs'],
    cta: 'Go Pro', highlight: true,
  },
]

export default function Landing() {
  return (
    <main>
      {/* Hero */}
      <section className="container-page grid items-center gap-14 pb-12 pt-16 lg:grid-cols-2 lg:pt-24">
        <div>
          <span className="badge animate-fade-up">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Spreadsheets → APIs
          </span>
          <h1 className="animate-fade-up delay-1 mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-6xl">
            Turn any spreadsheet into a <span className="text-gradient">live REST API</span> in seconds.
          </h1>
          <p className="animate-fade-up delay-2 mt-6 max-w-xl text-lg text-slate-400">
            Upload a CSV and instantly get a secure, queryable JSON endpoint — with filtering,
            sorting, pagination and API keys. Zero backend code.
          </p>
          <div className="animate-fade-up delay-3 mt-8 flex flex-wrap items-center gap-3">
            <Link to="/signup" className="btn-primary px-6 py-3 text-base">
              Get started free <IconArrowRight width={18} height={18} />
            </Link>
            <a href="#how" className="btn-ghost px-6 py-3 text-base">See how it works</a>
          </div>
          <p className="animate-fade-up delay-4 mt-5 text-sm text-slate-500">
            No credit card · Free tier forever
          </p>
        </div>
        <div className="animate-float">
          <ApiDemo />
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="container-page py-24">
        <SectionHeading eyebrow="How it works" title="Three steps from file to API" />
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.title} className="card card-hover relative p-7">
              <span className="absolute right-6 top-5 font-mono text-5xl font-bold text-white/5">0{i + 1}</span>
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500/20 to-accent-500/10 text-brand-300 ring-1 ring-inset ring-white/10">
                <s.icon width={22} height={22} />
              </span>
              <h3 className="mt-5 text-lg font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="container-page py-12">
        <SectionHeading eyebrow="Features" title="Engineered like a real product" />
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="card card-hover p-6">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-brand-300">
                <f.icon width={20} height={20} />
              </span>
              <h3 className="mt-4 font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="container-page py-24">
        <SectionHeading eyebrow="Pricing" title="Simple, honest pricing" />
        <div className="mx-auto mt-14 grid max-w-3xl gap-6 sm:grid-cols-2">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`card relative p-8 ${t.highlight ? 'ring-2 ring-brand-500/50' : ''}`}
            >
              {t.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-brand-500 to-brand-600 px-3 py-1 text-xs font-semibold text-white shadow-lg shadow-brand-600/40">
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-white">{t.name}</h3>
              <p className="mt-1 text-sm text-slate-400">{t.blurb}</p>
              <div className="mt-5 flex items-end gap-1">
                <span className="text-4xl font-extrabold text-white">{t.price}</span>
                {t.per && <span className="mb-1 text-slate-400">{t.per}</span>}
              </div>
              <ul className="mt-6 space-y-3 text-sm">
                {t.features.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-slate-300">
                    <IconCheck width={16} height={16} className="text-brand-300" /> {f}
                  </li>
                ))}
              </ul>
              <Link
                to="/signup"
                className={`${t.highlight ? 'btn-primary' : 'btn-ghost'} mt-8 w-full`}
              >
                {t.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="container-page py-12">
        <div className="card relative overflow-hidden p-12 text-center">
          <div className="absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full bg-brand-600/30 blur-3xl" />
          <h2 className="relative text-3xl font-bold text-white">Ship your first API in 60 seconds.</h2>
          <p className="relative mx-auto mt-3 max-w-md text-slate-400">
            Sign up, upload a spreadsheet, copy your key. That's the whole setup.
          </p>
          <Link to="/signup" className="btn-primary relative mt-8 px-6 py-3 text-base">
            Create your free account <IconArrowRight width={18} height={18} />
          </Link>
        </div>
      </section>

      <Footer />
    </main>
  )
}

function SectionHeading({ eyebrow, title }) {
  return (
    <div className="text-center">
      <p className="text-sm font-semibold uppercase tracking-widest text-brand-300">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">{title}</h2>
    </div>
  )
}
