import { NavLink } from "react-router-dom";

const TRACKS = [
  { to: "/sql", label: "SQL" },
  { to: "/ai-ml", label: "AI/ML" },
  { to: "/dsa", label: "DSA" },
  { to: "/gym", label: "GYM" },
];

export default function SideRail() {
  return (
    <nav className="fixed right-0 top-1/2 -translate-y-1/2 z-20 hidden lg:flex flex-col items-end gap-5 pr-4">
      {TRACKS.map((track) => (
        <NavLink
          key={track.to}
          to={track.to}
          className={({ isActive }) =>
            `group flex items-center gap-2 font-display text-[11px] tracking-[0.25em] uppercase transition-colors ${
              isActive ? "text-cyan-bright" : "text-white/50 hover:text-white/85"
            }`
          }
        >
          {({ isActive }) => (
            <>
              <span>{track.label}</span>
              <span
                className={`inline-block text-[10px] transition-transform ${
                  isActive ? "text-gold-bright" : "text-gold/60 group-hover:translate-x-0.5"
                }`}
              >
                &#10094;
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
