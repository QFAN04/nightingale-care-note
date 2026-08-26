"use client";

import { useState } from "react";

import { CareGlance } from "@/components/care-glance";
import { useDemoIdentity } from "@/components/demo-identity-context";
import { ScribeModal } from "@/components/scribe-modal";
import { TimelineCard } from "@/components/timeline-card";
import { sarahGlance, sarahLim, sarahTimeline, type TimelineItem } from "@/lib/demo-data";
import type { ScribeResult } from "@/lib/scribe-api";

const SARAH_PATIENT_ID = "00000000-0000-0000-0000-000000000002";

export function CareNoteWorkspace() {
  const { identity } = useDemoIdentity();
  const [isScribeOpen, setIsScribeOpen] = useState(false);
  const [timeline, setTimeline] = useState<TimelineItem[]>(sarahTimeline);

  function addScribeResult(result: ScribeResult) {
    const now = new Date();
    const item: TimelineItem = {
      id: `scribe-${now.getTime()}`,
      date: now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
      time: now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
      label: "AI doctor consult summary",
      title: "New AI scribe summary",
      content: result.summary,
      author: "AI scribed from clinician consultation",
      tone: "ai-clinician",
      review: "Pending review",
    };
    setTimeline((current) => [item, ...current]);
  }

  return (
    <main id="workspace" className="px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-col gap-5 border-b border-[#dce6e2] pb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-[#667773]">
              <span>{sarahLim.externalRef}</span><span aria-hidden="true">•</span><span>{sarahLim.clinic}</span>
            </div>
            <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[#172522] sm:text-4xl">{sarahLim.name}</h2>
            <p className="mt-2 text-sm text-[#667773]">{sarahLim.detail}</p>
          </div>
          <button className="w-fit rounded-xl bg-[#176b5b] px-4 py-2.5 text-sm font-semibold text-white shadow-sm" onClick={() => setIsScribeOpen(true)} type="button">
            New AI Scribe
          </button>
        </div>

        <CareGlance currentUserId={identity.id} sections={sarahGlance} />

        <section aria-labelledby="timeline-heading" className="mt-8">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">Care note</p>
              <h3 className="mt-1 text-xl font-semibold tracking-[-0.025em] text-[#20332f]" id="timeline-heading">Longitudinal timeline</h3>
            </div>
            <span className="text-xs text-[#778782]">Newest first</span>
          </div>
          <ol className="mt-5 space-y-4">
            {timeline.map((item) => (
              <li className="grid gap-3 sm:grid-cols-[110px_1fr]" key={item.id}>
                <div className="pt-2 sm:text-right"><p className="text-sm font-semibold text-[#415a54]">{item.date}</p><p className="mt-1 text-xs text-[#82908c]">{item.time}</p></div>
                <TimelineCard
                  canCollaborate={identity.role === "staff" || identity.role === "clinician"}
                  currentUserId={identity.id}
                  item={item}
                  showInternalComments={identity.role !== "patient"}
                />
              </li>
            ))}
          </ol>
        </section>
      </div>
      {isScribeOpen ? <ScribeModal currentUserId={identity.id} onClose={() => setIsScribeOpen(false)} onComplete={addScribeResult} patientId={SARAH_PATIENT_ID} /> : null}
    </main>
  );
}
