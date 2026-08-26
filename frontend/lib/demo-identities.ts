export type DemoRole = "patient" | "staff" | "clinician" | "admin";

export type DemoIdentity = {
  id: string;
  role: DemoRole;
  label: string;
  displayName: string;
};

export const demoIdentities: DemoIdentity[] = [
  {
    id: "00000000-0000-0000-0000-000000000003",
    role: "patient",
    label: "Patient",
    displayName: "Sarah Lim",
  },
  {
    id: "00000000-0000-0000-0000-000000000004",
    role: "staff",
    label: "Staff",
    displayName: "Amanda Wong",
  },
  {
    id: "00000000-0000-0000-0000-000000000005",
    role: "clinician",
    label: "Clinician",
    displayName: "Dr Priya Nair",
  },
  {
    id: "00000000-0000-0000-0000-000000000006",
    role: "admin",
    label: "Admin",
    displayName: "Daniel Tan",
  },
];

export const defaultDemoIdentity = demoIdentities.find(
  (identity) => identity.role === "clinician",
)!;
