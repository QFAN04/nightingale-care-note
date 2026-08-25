import { TimelineCard } from "@/components/timeline-card";
import { sarahLim, sarahTimeline } from "@/lib/demo-data";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#f4f8f6]">
      <header className="sticky top-0 z-10 border-b border-[#dce6e2] bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 sm:px-8">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="grid size-9 place-items-center rounded-xl bg-[#176b5b] text-sm font-semibold text-white shadow-sm"
            >
              N
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-[-0.02em] text-[#172522]">
                Nightingale
              </h1>
              <p className="hidden text-xs text-[#667773] sm:block">
                Longitudinal care, clearly understood.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden text-xs font-medium uppercase tracking-[0.12em] text-[#758680] sm:inline">
              Synthetic demo
            </span>
            <button
              className="flex items-center gap-2 rounded-full border border-[#cfe0da] bg-[#f7fbf9] px-3 py-2 text-sm font-medium text-[#285f54]"
              type="button"
            >
              <span aria-hidden="true" className="size-2 rounded-full bg-[#2d8b75]" />
              Clinician view
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[260px_1fr]">
        <aside className="hidden min-h-[calc(100vh-4rem)] border-r border-[#dce6e2] bg-white px-4 py-6 lg:block">
          <p className="px-3 text-xs font-semibold uppercase tracking-[0.14em] text-[#71817d]">
            Patients
          </p>
          <nav aria-label="Patient list" className="mt-3">
            <a
              aria-current="page"
              className="flex items-center gap-3 rounded-xl bg-[#e4f3ee] px-3 py-3"
              href="#workspace"
            >
              <span className="grid size-9 place-items-center rounded-full bg-white text-xs font-semibold text-[#176b5b]">
                SL
              </span>
              <span>
                <span className="block text-sm font-semibold text-[#24413a]">Sarah Lim</span>
                <span className="block text-xs text-[#6d817b]">PAT-001 · Active</span>
              </span>
            </a>
          </nav>

          <div className="mt-8 rounded-2xl border border-[#dce6e2] bg-[#f8fbfa] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#667773]">
              Trust boundary
            </p>
            <p className="mt-2 text-sm leading-6 text-[#536560]">
              AI entries remain distinct and traceable to their source record.
            </p>
          </div>
        </aside>

        <main id="workspace" className="px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
          <div className="mx-auto max-w-5xl">
            <div className="flex flex-col gap-5 border-b border-[#dce6e2] pb-7 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-[#667773]">
                  <span>{sarahLim.externalRef}</span>
                  <span aria-hidden="true">•</span>
                  <span>{sarahLim.clinic}</span>
                </div>
                <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[#172522] sm:text-4xl">
                  {sarahLim.name}
                </h2>
                <p className="mt-2 text-sm text-[#667773]">{sarahLim.detail}</p>
              </div>
              <button
                className="w-fit rounded-xl bg-[#176b5b] px-4 py-2.5 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
                disabled
                title="Available in the AI Scribe gate"
                type="button"
              >
                New AI Scribe
              </button>
            </div>

            <section aria-labelledby="timeline-heading" className="mt-8">
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">
                    Care note
                  </p>
                  <h3
                    className="mt-1 text-xl font-semibold tracking-[-0.025em] text-[#20332f]"
                    id="timeline-heading"
                  >
                    Longitudinal timeline
                  </h3>
                </div>
                <span className="text-xs text-[#778782]">Newest first</span>
              </div>

              <ol className="mt-5 space-y-4">
                {sarahTimeline.map((item) => (
                  <li className="grid gap-3 sm:grid-cols-[110px_1fr]" key={item.id}>
                    <div className="pt-2 sm:text-right">
                      <p className="text-sm font-semibold text-[#415a54]">{item.date}</p>
                      <p className="mt-1 text-xs text-[#82908c]">{item.time}</p>
                    </div>
                    <TimelineCard item={item} />
                  </li>
                ))}
              </ol>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
