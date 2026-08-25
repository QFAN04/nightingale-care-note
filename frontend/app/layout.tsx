import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nightingale Care Note",
  description: "Longitudinal clinical context with traceable AI assistance.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
