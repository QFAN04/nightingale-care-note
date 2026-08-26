"use client";

import { FormEvent, useState } from "react";

import { runScribe, type ScribeResult } from "@/lib/scribe-api";

type ScribeModalProps = {
  patientId: string;
  currentUserId: string;
  onClose: () => void;
  onComplete: (result: ScribeResult) => void;
};

export function ScribeModal({ currentUserId, patientId, onClose, onComplete }: ScribeModalProps) {
  const [transcript, setTranscript] = useState("");
  const [result, setResult] = useState<ScribeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const nextResult = await runScribe(
        patientId,
        "doctor_patient",
        transcript,
        currentUserId,
      );
      setResult(nextResult);
      onComplete(nextResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "AI Scribe failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#10201c]/45 p-4 backdrop-blur-sm">
      <section
        aria-labelledby="scribe-title"
        aria-modal="true"
        className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-[#d5e2de] bg-white shadow-2xl"
        role="dialog"
      >
        <div className="flex items-start justify-between border-b border-[#e0e9e6] px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">AI consultation</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-[#172522]" id="scribe-title">
              New AI Scribe
            </h2>
          </div>
          <button aria-label="Close AI Scribe" className="rounded-full px-3 py-1.5 text-xl text-[#60736d] hover:bg-[#eef5f2]" onClick={onClose} type="button">
            ×
          </button>
        </div>

        <form className="space-y-5 p-6" onSubmit={handleSubmit}>
          <label className="block text-sm font-semibold text-[#304a44]">
            Interaction type
            <select
              className="mt-2 w-full rounded-xl border border-[#cddcd7] bg-[#f9fbfa] px-3 py-2.5 font-normal text-[#263b36]"
              defaultValue="doctor_patient"
            >
              <option value="doctor_patient">Doctor–patient consultation</option>
            </select>
          </label>

          <label className="block text-sm font-semibold text-[#304a44]">
            Transcript
            <textarea
              className="mt-2 min-h-40 w-full resize-y rounded-xl border border-[#cddcd7] bg-[#f9fbfa] px-3 py-3 font-normal leading-6 text-[#263b36] outline-none focus:border-[#2d8b75] focus:ring-2 focus:ring-[#cde7df]"
              onChange={(event) => setTranscript(event.target.value)}
              placeholder={"Doctor: ...\nPatient: ..."}
              required
              value={transcript}
            />
          </label>

          <div className="rounded-xl border border-[#dce6e2] bg-[#f5faf8] px-4 py-3 text-sm leading-6 text-[#536560]">
            Known patient identifiers are deterministically redacted before the transcript reaches DeepSeek.
          </div>

          {error ? <p className="rounded-xl bg-[#fff0ed] px-4 py-3 text-sm text-[#9a392a]" role="alert">{error}</p> : null}

          <button
            className="w-full rounded-xl bg-[#176b5b] px-4 py-3 text-sm font-semibold text-white shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSubmitting || transcript.trim().length === 0}
            type="submit"
          >
            {isSubmitting ? "Generating…" : "Generate"}
          </button>
        </form>

        {result ? (
          <div className="border-t border-[#e0e9e6] bg-[#f8fbfa] px-6 py-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#176b5b]">
              <span aria-hidden="true">✓</span>
              <span>PHI redacted</span>
            </div>
            <h3 className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-[#667773]">AI summary</h3>
            <p className="mt-2 text-sm leading-6 text-[#304a44]">{result.summary}</p>
            <h3 className="mt-5 text-xs font-semibold uppercase tracking-[0.12em] text-[#667773]">Extracted facts</h3>
            <ul className="mt-2 space-y-2">
              {result.facts.map((fact, index) => (
                <li className="rounded-xl border border-[#dce6e2] bg-white px-4 py-3" key={`${fact.entity_name}-${index}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-[#263b36]">{fact.entity_name}</span>
                    <span className="rounded-full bg-[#fff0d9] px-2 py-1 text-xs font-semibold uppercase text-[#8a5815]">{fact.risk_hint} hint</span>
                  </div>
                  <p className="mt-1 text-xs text-[#6b7e78]">“{fact.source_quote}”</p>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs font-semibold text-[#176b5b]">Added to the top of the timeline</p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
