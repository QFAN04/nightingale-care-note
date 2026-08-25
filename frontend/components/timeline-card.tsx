import type { TimelineItem } from "@/lib/demo-data";

const toneStyles: Record<TimelineItem["tone"], string> = {
  clinician: "border-l-[#176b5b]",
  staff: "border-l-[#6f8c84]",
  "ai-patient": "border-l-[#8562a7]",
  "ai-clinician": "border-l-[#427a9b]",
};

const badgeStyles: Record<TimelineItem["tone"], string> = {
  clinician: "bg-[#e7f3ef] text-[#176b5b]",
  staff: "bg-[#eef2f1] text-[#536b65]",
  "ai-patient": "bg-[#f2edf7] text-[#745390]",
  "ai-clinician": "bg-[#eaf2f7] text-[#356c8b]",
};

export function TimelineCard({ item }: { item: TimelineItem }) {
  return (
    <article
      className={`rounded-2xl border border-l-4 border-[#dce6e2] bg-white p-5 shadow-[0_1px_2px_rgba(23,37,34,0.04)] ${toneStyles[item.tone]}`}
      id={item.id}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] ${badgeStyles[item.tone]}`}
          >
            {item.label}
          </span>
          <h4 className="mt-3 text-base font-semibold tracking-[-0.015em] text-[#20332f]">
            {item.title}
          </h4>
        </div>
        {item.review && (
          <span className="rounded-full border border-[#d7e2de] px-2.5 py-1 text-xs font-medium text-[#61736e]">
            {item.review}
          </span>
        )}
      </div>
      <p className="mt-3 text-sm leading-6 text-[#536560]">{item.content}</p>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[#edf2f0] pt-4 text-xs text-[#74837f]">
        <span>{item.author}</span>
        {item.sourceId && (
          <a
            className="font-semibold text-[#176b5b] underline decoration-[#a9cfc5] underline-offset-4"
            href={`#${item.sourceId}`}
          >
            View source
          </a>
        )}
      </div>
    </article>
  );
}
