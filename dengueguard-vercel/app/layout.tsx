import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import { DataProvider } from "@/components/DataProvider";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "DengueGuard | ระบบเฝ้าระวังและป้องกันโรคไข้เลือดออก",
  description:
    "ระบบพยากรณ์ความเสี่ยงโรคไข้เลือดออก ระบบป้องกันเชิงรุก และแบบคัดกรองอาการเบื้องต้น สำหรับพื้นที่ สคร.4",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th">
      <body>
        <DataProvider>
          <AppShell>{children}</AppShell>
        </DataProvider>
      </body>
    </html>
  );
}
