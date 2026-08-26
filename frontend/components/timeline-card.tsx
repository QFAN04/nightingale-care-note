import type { TimelineItem } from "@/lib/demo-data";
import { CommentThread } from "@/components/comment-thread";

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

export function TimelineCard({
  canCollaborate,
  currentUserId,
  item,
  showInternalComments,
}: {
  canCollaborate: boolean;
  currentUserId: string;
  item: TimelineItem;
  showInternalComments: boolean;
}) {
  return (
    <article
      className={`scroll-mt-24 rounded-2xl border border-l-4 border-[#dce6e2] bg-white p-5 shadow-[0_1px_2px_rgba(23,37,34,0.04)] target:border-[#82ab9f] target:bg-[#fbfefd] target:ring-4 target:ring-[#d7ebe5] ${toneStyles[item.tone]}`}
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
      {item.sourceEvidence && (
        <div className="mt-4 rounded-xl border border-[#e0e9e6] bg-[#f7faf9] px-3.5 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#687a75]">
            Source evidence
          </p>
          <p className="mt-1.5 text-xs leading-5 text-[#4f625d]">
            “<mark className="rounded-sm bg-[#fff0a8] px-0.5 text-inherit">{item.sourceEvidence}</mark>”
          </p>
        </div>
      )}
      {showInternalComments && item.apiId && item.comments ? (
        <CommentThread
          canCollaborate={canCollaborate}
          currentUserId={currentUserId}
          entryId={item.apiId}
          initialComments={item.comments}
        />
      ) : null}
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
