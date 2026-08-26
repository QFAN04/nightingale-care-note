"use client";

import { useState } from "react";

import type { GlanceSection } from "@/lib/demo-data";
import { reviewHighlight, type HighlightReviewAction } from "@/lib/highlight-api";

const sectionStyles: Record<GlanceSection["id"], { accent: string; badge: string; dot: string }> = {
  critical: {
    accent: "border-t-[#b44c43]",
    badge: "bg-[#f9e9e6] text-[#913e37]",
    dot: "bg-[#b44c43]",
  },
  recent: {
    accent: "border-t-[#b8782f]",
    badge: "bg-[#fbf0df] text-[#8a5a25]",
    dot: "bg-[#c48235]",
  },
  actions: {
    accent: "border-t-[#3b7392]",
    badge: "bg-[#e9f2f7] text-[#356b87]",
    dot: "bg-[#427a9b]",
  },
  conflicts: {
    accent: "border-t-[#7a6295]",
    badge: "bg-[#f1ebf6] text-[#6d5488]",
    dot: "bg-[#80669b]",
  },
};

export function CareGlance({
  currentUserId,
  sections,
}: {
  currentUserId: string;
  sections: GlanceSection[];
}) {
  const [visibleSections, setVisibleSections] = useState(sections);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  async function handleReview(highlightId: string, action: HighlightReviewAction) {
    setPendingId(highlightId);
    setReviewError(null);
    try {
      const result = await reviewHighlight(highlightId, action, currentUserId);
      setVisibleSections((current) =>
        current.map((section) => ({
          ...section,
          items:
            result.status === "rejected"
              ? section.items.filter((item) => item.id !== highlightId)
              : section.items.map((item) =>
                  item.id === highlightId
                    ? {
                        ...item,
                        status: "Accepted",
                        reviewable: false,
                        acceptedBy: result.reviewed_by.display_name,
                      }
                    : item,
                ),
        })),
      );
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "The review could not be saved.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <section aria-labelledby="care-glance-heading" className="mt-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">
            Prioritised care state
          </p>
          <h3
            className="mt-1 text-xl font-semibold tracking-[-0.025em] text-[#20332f]"
            id="care-glance-heading"
          >
            Care Glance
          </h3>
        </div>
        <p className="max-w-md text-xs leading-5 text-[#6b7b77] sm:text-right">
          A concise, explainable view. Open any item to inspect its evidence and source.
        </p>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {visibleSections.map((section) => {
          const styles = sectionStyles[section.id];
          const headingId = `glance-${section.id}-heading`;
          return (
            <section
              aria-labelledby={headingId}
              className={`rounded-2xl border border-t-4 border-[#dce6e2] bg-white p-5 shadow-[0_1px_2px_rgba(23,37,34,0.04)] ${styles.accent}`}
              key={section.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span aria-hidden="true" className={`size-2 rounded-full ${styles.dot}`} />
                    <h4 className="text-sm font-semibold text-[#20332f]" id={headingId}>
                      {section.title}
                    </h4>
                  </div>
                  <p className="mt-1 pl-4 text-xs text-[#778782]">{section.eyebrow}</p>
                </div>
                <span className="rounded-full bg-[#f1f5f3] px-2 py-1 text-[11px] font-semibold text-[#667773]">
                  {section.items.length}
                </span>
              </div>

              <div className="mt-4 space-y-3">
                {section.items.map((item) => (
                  <article className="rounded-xl bg-[#f8fbfa] p-4" key={item.id}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <h5 className="max-w-[80%] text-sm font-semibold leading-5 text-[#253a35]">
                        {item.title}
                      </h5>
                      <span className={`rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.06em] ${styles.badge}`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-[#5f716c]">
                      <span className="font-semibold text-[#425a54]">Why it matters: </span>
                      {item.riskReason}
                    </p>

                    {item.reviewable ? (
                      <div className="mt-3 rounded-lg border border-[#e7dded] bg-[#f8f4fb] p-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#745390]">
                          ◇ AI suggestion
                        </p>
                        <div className="mt-2 flex gap-2">
                          <button
                            className="rounded-lg bg-[#176b5b] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                            disabled={pendingId === item.id}
                            onClick={() => void handleReview(item.id, "accept")}
                            type="button"
                          >
                            Accept
                          </button>
                          <button
                            className="rounded-lg border border-[#d4dfdb] bg-white px-3 py-1.5 text-xs font-semibold text-[#536660] disabled:opacity-60"
                            disabled={pendingId === item.id}
                            onClick={() => void handleReview(item.id, "reject")}
                            type="button"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    ) : null}
                    {item.acceptedBy ? (
                      <p className="mt-3 text-xs font-semibold text-[#176b5b]">
                        ✓ Accepted by {item.acceptedBy}
                      </p>
                    ) : null}

                    <details className="group mt-3 border-t border-[#e4ece9] pt-3">
                      <summary className="cursor-pointer list-none text-xs font-semibold text-[#176b5b] marker:content-none">
                        <span className="flex items-center justify-between">
                          Evidence &amp; details
                          <span aria-hidden="true" className="text-base leading-none group-open:rotate-45">
                            +
                          </span>
                        </span>
                      </summary>
                      <div className="mt-3 rounded-lg border border-[#dfe9e5] bg-white p-3">
                        <blockquote className="text-xs italic leading-5 text-[#596b66]">
                          “{item.evidence}”
                        </blockquote>
                        <ul className="mt-3 flex flex-wrap gap-2">
                          {item.details.map((detail) => (
                            <li className="rounded-md bg-[#eef4f1] px-2 py-1 text-[11px] text-[#536660]" key={detail}>
                              {detail}
                            </li>
                          ))}
                        </ul>
                        <a
                          className="mt-3 inline-flex text-xs font-semibold text-[#176b5b] underline decoration-[#a9cfc5] underline-offset-4"
                          href={`#${item.sourceId}`}
                        >
                          Jump to source
                        </a>
                      </div>
                    </details>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      {reviewError ? (
        <p className="mt-3 text-sm text-[#9b413b]" role="alert">
          {reviewError}
        </p>
      ) : null}
    </section>
  );
}
