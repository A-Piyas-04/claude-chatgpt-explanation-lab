import type { Metadata } from "next";
import React from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "ExplanationLab",
  description:
    "Research platform for measuring and improving the human comprehensibility of AI-generated explanations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
