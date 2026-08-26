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

export type EntryVersion = {
  version_number: number;
  content: string;
  changed_by: { id: string; display_name: string };
  changed_at: string;
  change_reason: string;
  source_version: number | null;
  reverted_from_version: number | null;
};

export type EntryDiffPart = { type: "unchanged" | "added" | "removed"; text: string };

export class EntryVersionConflictError extends Error {
  constructor(public readonly currentVersion: number) {
    super("This note changed after you opened it. The latest version has been reloaded.");
  }
}

export async function fetchEntryVersions(entryId: string, currentUserId: string): Promise<EntryVersion[]> {
  return requestJson(`/api/v1/entries/${entryId}/versions`, currentUserId);
}

export async function fetchEntryDiff(entryId: string, fromVersion: number, toVersion: number, currentUserId: string): Promise<EntryDiffPart[]> {
  const result = await requestJson<{ diff: EntryDiffPart[] }>(
    `/api/v1/entries/${entryId}/diff?from_version=${fromVersion}&to_version=${toVersion}`,
    currentUserId,
  );
  return result.diff;
}

export async function updateEntry(entryId: string, content: string, expectedVersion: number, currentUserId: string): Promise<void> {
  await requestJson(`/api/v1/entries/${entryId}`, currentUserId, {
    method: "PATCH",
    body: JSON.stringify({ content, expected_version: expectedVersion }),
  });
}

export async function revertEntry(entryId: string, targetVersion: number, expectedVersion: number, currentUserId: string): Promise<void> {
  await requestJson(`/api/v1/entries/${entryId}/revert`, currentUserId, {
    method: "POST",
    body: JSON.stringify({ target_version: targetVersion, expected_version: expectedVersion }),
  });
}

async function requestJson<T = unknown>(url: string, currentUserId: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Demo-User-ID": currentUserId,
      ...init?.headers,
    },
  });
  const body = (await response.json().catch(() => null)) as ({ detail?: string; error?: string; current_version?: number } & T) | null;
  if (!response.ok) {
    if (response.status === 409 && body?.error === "version_conflict") {
      throw new EntryVersionConflictError(body.current_version ?? 0);
    }
    throw new Error(body?.detail ?? "The entry operation could not be completed.");
  }
  return body as T;
}
