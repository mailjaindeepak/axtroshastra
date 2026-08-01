import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/episodes", label: "Episodes" },
  { to: "/log", label: "Log Today" },
];

export default function TopNav() {
  return (
    <header className="flex items-center justify-between px-6 md:px-10 py-4 border-b border-gold/10">
      <div className="flex items-baseline gap-2">
        <span className="font-display text-lg tracking-[0.15em] text-gold-bright text-glow-gold">
          LOOP
        </span>
        <span className="font-display text-lg tracking-[0.15em] text-white/80">
          BREAKER
        </span>
      </div>
      <nav className="flex items-center gap-8">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `font-display text-[13px] tracking-[0.2em] uppercase transition-colors ${
                isActive ? "text-cyan-bright text-glow-cyan" : "text-white/60 hover:text-white/90"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
