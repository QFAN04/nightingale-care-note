"use client";

import { FormEvent, useState } from "react";

import { createManualEntry } from "@/lib/entry-api";
import type { DemoRole } from "@/lib/demo-identities";

type AddNoteModalProps = {
  patientId: string;
  currentUserId: string;
  role: Extract<DemoRole, "staff" | "clinician">;
  onClose: () => void;
  onComplete: () => void | Promise<void>;
};

export function AddNoteModal({
  currentUserId,
  patientId,
  role,
  onClose,
  onComplete,
}: AddNoteModalProps) {
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const title = role === "staff" ? "Add staff note" : "Add clinician note";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await createManualEntry(patientId, content.trim(), currentUserId);
      await onComplete();
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The note could not be saved.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#10201c]/45 p-4 backdrop-blur-sm">
      <section aria-labelledby="add-note-title" aria-modal="true" className="w-full max-w-xl rounded-3xl border border-[#d5e2de] bg-white shadow-2xl" role="dialog">
        <div className="flex items-start justify-between border-b border-[#e0e9e6] px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">Manual care record</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-[#172522]" id="add-note-title">{title}</h2>
          </div>
          <button aria-label="Close note editor" className="rounded-full px-3 py-1.5 text-xl text-[#60736d] hover:bg-[#eef5f2]" onClick={onClose} type="button">×</button>
        </div>
        <form className="space-y-5 p-6" onSubmit={handleSubmit}>
          <label className="block text-sm font-semibold text-[#304a44]">
            Note content
            <textarea className="mt-2 min-h-40 w-full resize-y rounded-xl border border-[#cddcd7] bg-[#f9fbfa] px-3 py-3 font-normal leading-6 text-[#263b36] outline-none focus:border-[#2d8b75] focus:ring-2 focus:ring-[#cde7df]" onChange={(event) => setContent(event.target.value)} required value={content} />
          </label>
          <p className="rounded-xl border border-[#dce6e2] bg-[#f5faf8] px-4 py-3 text-sm leading-6 text-[#536560]">The note type and author are derived from your authenticated demo role.</p>
          {error ? <p className="rounded-xl bg-[#fff0ed] px-4 py-3 text-sm text-[#9a392a]" role="alert">{error}</p> : null}
          <button className="w-full rounded-xl bg-[#176b5b] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={isSubmitting || content.trim().length === 0} type="submit">{isSubmitting ? "Saving…" : "Save note"}</button>
        </form>
      </section>
    </div>
  );
}
