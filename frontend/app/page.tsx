export default function Home() {
  return (
    <div className="min-h-screen bg-[#f4f8f6]">
      <header className="border-b border-[#dce6e2] bg-white">
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
              <p className="text-xs text-[#667773]">
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
              <span
                aria-hidden="true"
                className="size-2 rounded-full bg-[#2d8b75]"
              />
              Clinician view
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[240px_1fr]">
        <aside className="hidden min-h-[calc(100vh-4rem)] border-r border-[#dce6e2] bg-white px-4 py-6 lg:block">
          <nav aria-label="Primary navigation" className="space-y-1">
            <a
              aria-current="page"
              className="block rounded-xl bg-[#e4f3ee] px-4 py-3 text-sm font-semibold text-[#176b5b]"
              href="#workspace"
            >
              Patients
            </a>
            <span className="block rounded-xl px-4 py-3 text-sm text-[#85928e]">
              Care activity
            </span>
            <span className="block rounded-xl px-4 py-3 text-sm text-[#85928e]">
              Audit overview
            </span>
          </nav>

          <div className="mt-10 rounded-2xl border border-[#dce6e2] bg-[#f8fbfa] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#667773]">
              Trust boundary
            </p>
            <p className="mt-2 text-sm leading-6 text-[#536560]">
              AI assistance remains traceable to the longitudinal source record.
            </p>
          </div>
        </aside>

        <main id="workspace" className="px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          <div className="mx-auto max-w-5xl">
            <div className="flex flex-col gap-4 border-b border-[#dce6e2] pb-7 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">
                  Patient workspace
                </p>
                <h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-[#172522]">
                  Care notes, with context intact
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-[#667773]">
                  The clinical timeline and Care Glance will appear here after
                  the domain and database gates are connected.
                </p>
              </div>
              <button
                className="w-fit rounded-xl bg-[#176b5b] px-4 py-2.5 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-45"
                disabled
                type="button"
              >
                New AI Scribe
              </button>
            </div>

            <section
              aria-labelledby="foundation-status"
              className="mt-8 grid gap-4 md:grid-cols-3"
            >
              <h3 className="sr-only" id="foundation-status">
                Foundation status
              </h3>
              {[
                ["Care Glance", "Awaiting clinical facts and trust rules"],
                ["Timeline", "Awaiting role-aware patient entries"],
                ["AI Scribe", "Awaiting PHI-safe provider pipeline"],
              ].map(([title, description]) => (
                <article
                  className="rounded-2xl border border-[#dce6e2] bg-white p-5 shadow-[0_1px_2px_rgba(23,37,34,0.04)]"
                  key={title}
                >
                  <div className="mb-5 h-1.5 w-10 rounded-full bg-[#b7d9cf]" />
                  <h4 className="font-semibold text-[#243a35]">{title}</h4>
                  <p className="mt-2 text-sm leading-6 text-[#6a7b76]">
                    {description}
                  </p>
                </article>
              ))}
            </section>

            <div className="mt-8 rounded-2xl border border-dashed border-[#b9cbc5] bg-white/60 px-6 py-10 text-center">
              <p className="text-sm font-medium text-[#415a54]">
                No synthetic patient records connected yet
              </p>
              <p className="mt-2 text-sm text-[#778782]">
                Sarah Lim will be introduced after the schema and fixture gates.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
