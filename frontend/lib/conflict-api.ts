export type ConflictResolutionResult = {
  id: string;
  status: "resolved";
  resolution_note: string;
  resolved_by: {
    id: string;
    display_name: string;
  };
  resolved_at: string;
};

export async function resolveConflict(
  conflictId: string,
  resolutionNote: string,
  currentUserId: string,
): Promise<ConflictResolutionResult> {
  const response = await fetch(`/api/v1/conflicts/${conflictId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-ID": currentUserId,
    },
    body: JSON.stringify({ resolution_note: resolutionNote }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The conflict resolution could not be saved.");
  }
  return (await response.json()) as ConflictResolutionResult;
}
