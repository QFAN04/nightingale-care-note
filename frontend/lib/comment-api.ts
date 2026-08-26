export type CommentResult = {
  id: string;
  entry_id: string;
  content: string;
  mentioned_role: "clinician" | null;
  author: { id: string; display_name: string };
  resolved: boolean;
  resolved_by: { id: string; display_name: string } | null;
  resolved_at: string | null;
  created_at: string;
};

async function parseCommentResponse(response: Response): Promise<CommentResult> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The comment could not be saved.");
  }
  return (await response.json()) as CommentResult;
}

export async function addComment(
  entryId: string,
  content: string,
  currentUserId: string,
): Promise<CommentResult> {
  return parseCommentResponse(
    await fetch(`/api/v1/entries/${entryId}/comments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Demo-User-ID": currentUserId,
      },
      body: JSON.stringify({ content }),
    }),
  );
}

export async function resolveComment(
  commentId: string,
  currentUserId: string,
): Promise<CommentResult> {
  return parseCommentResponse(
    await fetch(`/api/v1/comments/${commentId}/resolve`, {
      method: "POST",
      headers: { "X-Demo-User-ID": currentUserId },
    }),
  );
}
