import React from "react";

import { Shell } from "@/components/shell";

/**
 * Researcher-facing layout group.
 *
 * The participant route at /p/[token] deliberately sits OUTSIDE this group so
 * it inherits none of the navigation, mode banners or researcher chrome. A
 * participant must not see experiment context while being assessed.
 */
export default function WorkbenchLayout({ children }: { children: React.ReactNode }) {
  return <Shell>{children}</Shell>;
}

/**
 * Every researcher route is rendered per request.
 *
 * These pages read live experiment state through an authenticated proxy, so
 * there is nothing meaningful to prerender at build time — and attempting it
 * would bake an empty shell into the bundle.
 */
export const dynamic = "force-dynamic";
