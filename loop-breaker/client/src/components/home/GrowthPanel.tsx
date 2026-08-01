import type { StatBlock } from "../../lib/types";
import Divider from "../ui/Divider";

interface GrowthRow extends StatBlock {
  levelThirtyDaysAgo: number;
}

export default function GrowthPanel({ rows, baselineLabel }: { rows: GrowthRow[]; baselineLabel: string }) {
  return (
    <div className="panel-glass rounded-lg p-5 md:p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-display text-sm tracking-[0.3em] uppercase text-cyan-bright text-glow-cyan">
          Growth
        </h2>
        <span className="font-mono text-[10px] text-white/35">vs {baselineLabel}</span>
      </div>
      <Divider variant="cyan" />
      <div className="flex flex-col gap-3 mt-5">
        {rows.map((row) => {
          const delta = row.level - row.levelThirtyDaysAgo;
          const deltaColor = delta > 0 ? "#6fae63" : delta < 0 ? "#e0685f" : "rgba(255,255,255,0.4)";
          return (
            <div key={row.key} className="flex items-center gap-3">
              <span className="font-display text-[12px] tracking-[0.1em] uppercase text-white/60 w-28 shrink-0">
                {row.label}
              </span>
              <div className="relative flex-1 h-1.5 rounded-full bg-black/40 border border-white/10 overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-white/15"
                  style={{ width: `${row.levelThirtyDaysAgo}%` }}
                />
                <div
                  className="absolute inset-y-0 left-0"
                  style={{
                    width: `${row.level}%`,
                    background: "linear-gradient(90deg, rgba(95,216,224,0.4), rgba(95,216,224,0.9))",
                  }}
                />
              </div>
              <span className="font-mono text-xs w-12 text-right" style={{ color: deltaColor }}>
                {delta > 0 ? "+" : ""}
                {delta}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
