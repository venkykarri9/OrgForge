import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OrgForge",
  description: "Salesforce story-to-deployment pipeline powered by AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
