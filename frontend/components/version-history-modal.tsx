"use client";

import { useEffect, useState } from "react";

import {
  EntryVersionConflictError,
  fetchEntryDiff,
  fetchEntryVersions,
  revertEntry,
  updateEntry,
  type EntryDiffPart,
  type EntryVersion,
} from "@/lib/entry-api";

type VersionHistoryModalProps = {
  entryId: string;
  currentContent: string;
  currentUserId: string;
  currentVersion: number;
  canManage: boolean;
  onClose: () => void;
  onComplete: () => void | Promise<void>;
};

export function VersionHistoryModal({ entryId, currentContent, currentUserId, currentVersion, canManage, onClose, onComplete }: VersionHistoryModalProps) {
  const [versions, setVersions] = useState<EntryVersion[]>([]);
  const [fromVersion, setFromVersion] = useState(1);
  const [toVersion, setToVersion] = useState(currentVersion);
  const [content, setContent] = useState(currentContent);
  const [diff, setDiff] = useState<EntryDiffPart[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    void fetchEntryVersions(entryId, currentUserId)
      .then((result) => {
        setVersions(result);
        if (result.length > 0) {
          setFromVersion(result[0].version_number);
          setToVersion(result[result.length - 1].version_number);
        }
      })
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Version history could not be loaded."));
  }, [currentUserId, entryId]);

  async function compareVersions() {
    setError(null);
    try {
      setDiff(await fetchEntryDiff(entryId, fromVersion, toVersion, currentUserId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Versions could not be compared.");
    }
  }

  async function saveRevision() {
    setIsBusy(true);
    setError(null);
    try {
      await updateEntry(entryId, content.trim(), currentVersion, currentUserId);
      await onComplete();
      onClose();
    } catch (caught) {
      if (caught instanceof EntryVersionConflictError) await onComplete();
      setError(caught instanceof Error ? caught.message : "The revision could not be saved.");
    } finally {
      setIsBusy(false);
    }
  }

  async function revert(targetVersion: number) {
    if (!window.confirm(`Revert to version ${targetVersion}? A new snapshot will be appended.`)) return;
    setIsBusy(true);
    setError(null);
    try {
      await revertEntry(entryId, targetVersion, currentVersion, currentUserId);
      await onComplete();
      onClose();
    } catch (caught) {
      if (caught instanceof EntryVersionConflictError) await onComplete();
      setError(caught instanceof Error ? caught.message : "The version could not be restored.");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#10201c]/45 p-4 backdrop-blur-sm">
      <section aria-labelledby="version-history-title" aria-modal="true" className="max-h-[92vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-[#d5e2de] bg-white shadow-2xl" role="dialog">
        <div className="flex items-start justify-between border-b border-[#e0e9e6] px-6 py-5">
          <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#176b5b]">Append-only revision history</p><h2 className="mt-1 text-2xl font-semibold text-[#172522]" id="version-history-title">Version history</h2></div>
          <button aria-label="Close version history" className="rounded-full px-3 py-1.5 text-xl text-[#60736d] hover:bg-[#eef5f2]" onClick={onClose} type="button">×</button>
        </div>
        <div className="space-y-6 p-6">
          {error ? <p className="rounded-xl bg-[#fff0ed] px-4 py-3 text-sm text-[#9a392a]" role="alert">{error}</p> : null}
          <ol className="space-y-2">
            {versions.map((version) => (
              <li className="rounded-xl border border-[#dce6e2] bg-[#f8fbfa] px-4 py-3" key={version.version_number}>
                <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold text-[#263b36]">Version {version.version_number}</span><span className="text-xs text-[#6b7e78]">{version.changed_by.display_name} · {version.change_reason.replaceAll("_", " ")}</span></div>
                <p className="mt-2 text-sm leading-6 text-[#536560]">{version.content}</p>
                {canManage && version.version_number < currentVersion ? <button className="mt-2 text-xs font-semibold text-[#176b5b] underline" disabled={isBusy} onClick={() => void revert(version.version_number)} type="button">Revert to version {version.version_number}</button> : null}
              </li>
            ))}
          </ol>
          {versions.length >= 2 ? (
            <section className="rounded-2xl border border-[#dce6e2] p-4" aria-label="Version comparison">
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs font-semibold text-[#536560]">From<select aria-label="From version" className="ml-2 rounded-lg border border-[#cddcd7] px-2 py-1" onChange={(event) => setFromVersion(Number(event.target.value))} value={fromVersion}>{versions.map((version) => <option key={version.version_number} value={version.version_number}>v{version.version_number}</option>)}</select></label>
                <label className="text-xs font-semibold text-[#536560]">To<select aria-label="To version" className="ml-2 rounded-lg border border-[#cddcd7] px-2 py-1" onChange={(event) => setToVersion(Number(event.target.value))} value={toVersion}>{versions.map((version) => <option key={version.version_number} value={version.version_number}>v{version.version_number}</option>)}</select></label>
                <button className="rounded-lg bg-[#176b5b] px-3 py-2 text-xs font-semibold text-white" onClick={() => void compareVersions()} type="button">Compare versions</button>
              </div>
              {diff.length > 0 ? <p className="mt-4 rounded-xl bg-[#f8fbfa] p-3 text-sm leading-7">{diff.map((part, index) => part.type === "added" ? <ins className="bg-[#dff3e8] text-[#176b5b] no-underline" key={index}>{part.text}</ins> : part.type === "removed" ? <del className="bg-[#ffe7e2] text-[#9a392a]" key={index}>{part.text}</del> : <span key={index}>{part.text}</span>)}</p> : null}
            </section>
          ) : null}
          {canManage ? (
            <section className="rounded-2xl border border-[#dce6e2] p-4" aria-label="Edit current version">
              <label className="block text-sm font-semibold text-[#304a44]">Current note content<textarea className="mt-2 min-h-32 w-full rounded-xl border border-[#cddcd7] bg-[#f9fbfa] px-3 py-3 font-normal" onChange={(event) => setContent(event.target.value)} value={content} /></label>
              <button className="mt-3 rounded-lg bg-[#176b5b] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50" disabled={isBusy || content.trim().length === 0 || content.trim() === currentContent.trim()} onClick={() => void saveRevision()} type="button">{isBusy ? "Saving…" : "Save revision"}</button>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
