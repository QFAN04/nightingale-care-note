"use client";

import { useDemoIdentity } from "@/components/demo-identity-context";
import { demoIdentities, type DemoRole } from "@/lib/demo-identities";

export function DemoRoleSwitcher() {
  const { identity, setRole } = useDemoIdentity();

  return (
    <div className="flex items-center gap-2 rounded-full border border-[#cfe0da] bg-[#f7fbf9] px-3 py-2 text-sm font-medium text-[#285f54]">
      <span aria-hidden="true" className="size-2 rounded-full bg-[#2d8b75]" />
      <label>
        <span className="sr-only">Demo role</span>
        <select
          aria-label="Demo role"
          className="cursor-pointer bg-transparent font-medium outline-none"
          onChange={(event) => setRole(event.target.value as DemoRole)}
          value={identity.role}
        >
          {demoIdentities.map((candidate) => (
            <option key={candidate.id} value={candidate.role}>
              {candidate.label} view
            </option>
          ))}
        </select>
      </label>
      <span aria-live="polite" className="sr-only">
        Viewing as {identity.displayName}
      </span>
    </div>
  );
}
