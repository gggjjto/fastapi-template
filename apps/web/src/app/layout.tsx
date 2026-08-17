import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rapid Development Template",
  description: "Business frontend for Rapid Development Template.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
