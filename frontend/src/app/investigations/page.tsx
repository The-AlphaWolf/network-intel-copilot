"use client";

import { Suspense } from "react";
import InvestigationsClient from "./InvestigationsClient";

export default function InvestigationsPage() {
  return (
    <Suspense fallback={null}>
      <InvestigationsClient />
    </Suspense>
  );
}
