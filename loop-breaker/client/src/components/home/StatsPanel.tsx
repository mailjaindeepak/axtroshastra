import type { StatBlock } from "../../lib/types";
import StatBar from "../ui/StatBar";
import Divider from "../ui/Divider";

export default function StatsPanel({ stats }: { stats: StatBlock[] }) {
  return (
    <div className="panel-glass rounded-lg p-5 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-sm tracking-[0.3em] uppercase text-gold-bright text-glow-gold">
          Status
        </h2>
        <span className="font-mono text-[10px] text-white/35">E · D · C · B · A · S</span>
      </div>
      <Divider variant="gold" />
      <div className="flex flex-col gap-4 mt-5">
        {stats.map((stat) => (
          <StatBar key={stat.key} label={stat.label} level={stat.level} note={stat.note} />
        ))}
      </div>
    </div>
  );
}
