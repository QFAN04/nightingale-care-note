"use client";

import { useState, type FormEvent } from "react";

import { addComment, resolveComment, type CommentResult } from "@/lib/comment-api";
import type { TimelineComment } from "@/lib/demo-data";

function toTimelineComment(comment: CommentResult): TimelineComment {
  return {
    id: comment.id,
    content: comment.content,
    author: comment.author.display_name,
    mentionedRole: comment.mentioned_role ?? undefined,
    resolved: comment.resolved,
    resolvedBy: comment.resolved_by?.display_name,
  };
}

export function CommentThread({
  canCollaborate,
  currentUserId,
  entryId,
  initialComments,
}: {
  canCollaborate: boolean;
  currentUserId: string;
  entryId: string;
  initialComments: TimelineComment[];
}) {
  const [comments, setComments] = useState(initialComments);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || saving) return;
    setSaving(true);
    setError(null);
    try {
      const created = await addComment(entryId, trimmed, currentUserId);
      setComments((current) => [...current, toTimelineComment(created)]);
      setContent("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The comment could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function markResolved(commentId: string) {
    setSaving(true);
    setError(null);
    try {
      const resolved = toTimelineComment(await resolveComment(commentId, currentUserId));
      setComments((current) =>
        current.map((comment) => (comment.id === commentId ? resolved : comment)),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The comment could not be resolved.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-label="Care team thread" className="mt-4 rounded-xl border border-[#dfe8e5] bg-[#f8fbfa] p-3.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#687a75]">Care team thread</p>
      <ul className="mt-3 space-y-2.5">
        {comments.map((comment) => (
          <li className="rounded-lg bg-white px-3 py-2.5 text-xs text-[#4f625d]" key={comment.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-[#34524b]">{comment.author}</p>
                <p className="mt-1 leading-5">{comment.content}</p>
              </div>
              {!comment.resolved && canCollaborate ? (
                <button aria-label="Resolve comment" className="font-semibold text-[#176b5b]" disabled={saving} onClick={() => markResolved(comment.id)} type="button">
                  Resolve
                </button>
              ) : null}
            </div>
            {comment.resolved ? <p className="mt-2 font-semibold text-[#176b5b]">Resolved by {comment.resolvedBy}</p> : <p className="mt-2 text-[#7b8985]">Open</p>}
          </li>
        ))}
      </ul>
      {canCollaborate ? (
        <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={submitComment}>
          <label className="sr-only" htmlFor={`comment-${entryId}`}>New comment</label>
          <input className="min-w-0 flex-1 rounded-lg border border-[#cfddd8] bg-white px-3 py-2 text-xs text-[#34524b]" id={`comment-${entryId}`} onChange={(event) => setContent(event.target.value)} placeholder="Add @clinician comment" value={content} />
          <button className="rounded-lg bg-[#176b5b] px-3 py-2 text-xs font-semibold text-white disabled:opacity-60" disabled={saving || !content.trim()} type="submit">Add comment</button>
        </form>
      ) : null}
      {error ? <p className="mt-2 text-xs font-medium text-[#a13d3d]" role="alert">{error}</p> : null}
    </section>
  );
}
