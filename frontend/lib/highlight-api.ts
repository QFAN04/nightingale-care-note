export type HighlightReviewAction = "accept" | "reject";

export type HighlightReviewResult = {
  id: string;
  status: "accepted" | "rejected";
  reviewed_by: {
    id: string;
    display_name: string;
  };
  reviewed_at: string;
};

const clinicianDemoUserId = "00000000-0000-0000-0000-000000000005";

export async function reviewHighlight(
  highlightId: string,
  action: HighlightReviewAction,
): Promise<HighlightReviewResult> {
  const response = await fetch(`/api/v1/highlights/${highlightId}/${action}`, {
    method: "POST",
    headers: { "X-Demo-User-ID": clinicianDemoUserId },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The highlight review could not be saved.");
  }
  return (await response.json()) as HighlightReviewResult;
}
