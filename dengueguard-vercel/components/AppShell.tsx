"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BellRing, ChevronRight, ClipboardCheck, LayoutDashboard, ShieldCheck } from "lucide-react";
import { SupportingPopup } from "@/components/SupportingPopup";
import { useDengueData } from "@/components/DataProvider";

const navigation = [
  { href: "/dashboard", label: "ภาพรวมสถานการณ์", icon: LayoutDashboard, sub: "Forecast dashboard" },
  { href: "/prevention", label: "ป้องกันเชิงรุก", icon: ShieldCheck, sub: "Early warning & prevention" },
  { href: "/symptom-checker", label: "ประเมินอาการเบื้องต้น", icon: ClipboardCheck, sub: "Symptom checker" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data, loading, error } = useDengueData();
  const latestDate = data?.predictions.map((row) => row.target_week_start).sort().at(-1);

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link href="/dashboard" className="brand-lockup">
          <div className="brand-mark">DG</div>
          <div className="brand-text"><strong>DengueGuard</strong><span>EARLY WARNING SYSTEM</span></div>
        </Link>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="เมนูหลัก">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href === "/dashboard" && pathname === "/");
            return (
              <Link href={item.href} key={item.href} className={`nav-item ${active ? "active" : ""}`}>
                <span className="nav-icon"><Icon size={19} /></span>
                <span className="nav-copy"><strong>{item.label}</strong><small>{item.sub}</small></span>
                {active && <ChevronRight size={16} className="nav-chevron" />}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-note">
          <div className="note-icon"><BellRing size={16} /></div>
          <strong>ข้อมูลเพื่อการเฝ้าระวัง</strong>
          <p>ผลพยากรณ์ใช้ประกอบการวางแผนป้องกัน ไม่ใช่การยืนยันการระบาดหรือการติดเชื้อรายบุคคล</p>
        </div>
        <div className="sidebar-footer"><span className="status-dot" /> DengueGuard · สคร.4</div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand"><div className="brand-mark small-mark">DG</div><strong>DengueGuard</strong></div>
          <div className="breadcrumb"><span>ระบบเฝ้าระวังโรค</span><ChevronRight size={14} /><strong>{navigation.find((item) => item.href === pathname)?.label ?? "DengueGuard"}</strong></div>
          <div className="topbar-right">
            <span className="topbar-status"><span className="status-dot" /> ระบบพร้อมใช้งาน</span>
            <span className="topbar-region">พื้นที่ สคร.4 · 8 จังหวัด</span>
          </div>
        </header>

        {error && <div className="global-error"><strong>โหลดข้อมูลไม่สำเร็จ</strong><span>{error}</span></div>}
        {loading ? (
          <main className="main-content"><div className="loading-card"><div className="spinner" /><strong>กำลังโหลดข้อมูล DengueGuard</strong><span>กำลังเตรียมข้อมูลพยากรณ์ สภาพอากาศ และแบบประเมิน</span></div></main>
        ) : (
          <main className="main-content">{children}</main>
        )}
        <footer className="site-footer">
          <span><Activity size={14} /> DengueGuard · Proactive Dengue Prevention and Early Warning System</span>
          <span>{latestDate ? `ข้อมูลพยากรณ์ล่าสุดในชุดข้อมูล: ${new Date(`${latestDate}T00:00:00`).toLocaleDateString("th-TH")}` : ""}</span>
        </footer>
      </div>
      {!loading && !error && <SupportingPopup />}
    </div>
  );
}
