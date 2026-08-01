import type { ReactNode } from "react";
import TopNav from "./TopNav";
import SideRail from "./SideRail";

export default function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-app-gradient text-white/90">
      <TopNav />
      <SideRail />
      <main className="pr-0 lg:pr-32">{children}</main>
    </div>
  );
}
