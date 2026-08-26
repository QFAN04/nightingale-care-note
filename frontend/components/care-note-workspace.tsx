"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { CareGlance } from "@/components/care-glance";
import { useDemoIdentity } from "@/components/demo-identity-context";
import { ScribeModal } from "@/components/scribe-modal";
import { TimelineCard } from "@/components/timeline-card";
import { fetchCareWorkspace } from "@/lib/care-api";
import {
  sarahGlance,
  sarahLim,
  sarahTimeline,
  type GlanceSection,
  type TimelineItem,
} from "@/lib/demo-data";

const SARAH_PATIENT_ID = "00000000-0000-0000-0000-000000000002";

export function CareNoteWorkspace() {
  const { identity } = useDemoIdentity();
  const [isScribeOpen, setIsScribeOpen] = useState(false);
  const [timeline, setTimeline] = useState<TimelineItem[]>(sarahTimeline);
  const [glance, setGlance] = useState<GlanceSection[]>(sarahGlance);
  const [loadedUserId, setLoadedUserId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const requestSequence = useRef(0);

  const loadRoleData = useCallback(async (userId: string, role: string) => {
    const sequence = ++requestSequence.current;
    try {
      const data = await fetchCareWorkspace(SARAH_PATIENT_ID, userId);
      if (sequence !== requestSequence.current) return;
      setTimeline(data.timeline);
      setGlance(data.sections);
      setLoadError(null);
    } catch (error) {
      if (sequence !== requestSequence.current) return;
      const fallback = fallbackForRole(role);
      setTimeline(fallback.timeline);
      setGlance(fallback.sections);
      setLoadError(
        error instanceof Error
          ? `${error.message} Showing the role-filtered synthetic preview.`
          : "Live care data is unavailable. Showing the role-filtered synthetic preview.",
      );
    } finally {
      if (sequence === requestSequence.current) {
        setLoadedUserId(userId);
      }
    }
  }, []);

  useEffect(() => {
    const sequence = ++requestSequence.current;
    void fetchCareWorkspace(SARAH_PATIENT_ID, identity.id)
      .then((data) => {
        if (sequence !== requestSequence.current) return;
        setTimeline(data.timeline);
        setGlance(data.sections);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (sequence !== requestSequence.current) return;
        const fallback = fallbackForRole(identity.role);
        setTimeline(fallback.timeline);
        setGlance(fallback.sections);
        setLoadError(
          error instanceof Error
            ? `${error.message} Showing the role-filtered synthetic preview.`
            : "Live care data is unavailable. Showing the role-filtered synthetic preview.",
        );
      })
      .finally(() => {
        if (sequence === requestSequence.current) setLoadedUserId(identity.id);
      });
  }, [identity.id, identity.role]);

  const isSwitchingRole = loadedUserId !== null && loadedUserId !== identity.id;
  const visibleTimeline = isSwitchingRole ? [] : timeline;
  const visibleGlance = isSwitchingRole ? emptyGlance() : glance;

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

        <CareGlance
          canReviewHighlights={identity.role === "clinician"}
          canResolveConflicts={identity.role === "clinician"}
          currentUserId={identity.id}
          key={identity.id}
          sections={visibleGlance}
        />

        {loadError ? (
          <p className="mt-4 rounded-xl border border-[#ead8bd] bg-[#fff9ef] px-4 py-3 text-xs text-[#805d2e]" role="status">
            {loadError}
          </p>
        ) : null}

        <section aria-labelledby="timeline-heading" className="mt-8">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">Care note</p>
              <h3 className="mt-1 text-xl font-semibold tracking-[-0.025em] text-[#20332f]" id="timeline-heading">Longitudinal timeline</h3>
            </div>
            <span className="text-xs text-[#778782]">Newest first</span>
          </div>
          {visibleTimeline.length === 0 ? (
            <p className="mt-5 rounded-2xl border border-[#dce6e2] bg-white px-5 py-6 text-sm text-[#667773]">
              No timeline entries visible for this role.
            </p>
          ) : (
          <ol className="mt-5 space-y-4">
            {visibleTimeline.map((item) => (
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
          )}
        </section>
      </div>
      {isScribeOpen ? <ScribeModal currentUserId={identity.id} onClose={() => setIsScribeOpen(false)} onComplete={() => loadRoleData(identity.id, identity.role)} patientId={SARAH_PATIENT_ID} /> : null}
    </main>
  );
}


function emptyGlance(): GlanceSection[] {
  return sarahGlance.map((section) => ({ ...section, items: [] }));
}


function fallbackForRole(role: string): {
  sections: GlanceSection[];
  timeline: TimelineItem[];
} {
  if (role !== "patient") return { sections: sarahGlance, timeline: sarahTimeline };
  return {
    sections: sarahGlance.map((section) => ({
      ...section,
      items:
        section.id === "critical"
          ? section.items.filter((item) => item.status === "Accepted")
          : [],
    })),
    timeline: [],
  };
}
