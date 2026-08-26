export async function createManualEntry(
  patientId: string,
  content: string,
  currentUserId: string,
): Promise<void> {
  const response = await fetch(`/api/v1/patients/${patientId}/entries`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-ID": currentUserId,
    },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? "The note could not be saved.");
  }
}
