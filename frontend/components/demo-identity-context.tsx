"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

import {
  defaultDemoIdentity,
  demoIdentities,
  type DemoIdentity,
  type DemoRole,
} from "@/lib/demo-identities";

type DemoIdentityContextValue = {
  identity: DemoIdentity;
  setRole: (role: DemoRole) => void;
};

const DemoIdentityContext = createContext<DemoIdentityContextValue | null>(null);

export function DemoIdentityProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState(defaultDemoIdentity);

  function setRole(role: DemoRole) {
    const nextIdentity = demoIdentities.find((candidate) => candidate.role === role);
    if (nextIdentity) {
      setIdentity(nextIdentity);
    }
  }

  return (
    <DemoIdentityContext.Provider value={{ identity, setRole }}>
      {children}
    </DemoIdentityContext.Provider>
  );
}

export function useDemoIdentity(): DemoIdentityContextValue {
  const context = useContext(DemoIdentityContext);
  if (context === null) {
    throw new Error("useDemoIdentity must be used within DemoIdentityProvider");
  }
  return context;
}
