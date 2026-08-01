import { motion } from "framer-motion";
import { rankForLevel, RANK_COLOR } from "../../lib/rank";
import RankBadge from "./RankBadge";

export default function StatBar({
  label,
  level,
  note,
}: {
  label: string;
  level: number;
  note?: string;
}) {
  const rank = rankForLevel(level);
  const color = RANK_COLOR[rank];

  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-display text-[13px] tracking-[0.15em] uppercase text-white/75">
          {label}
        </span>
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-sm text-white/70">{level}</span>
          <RankBadge rank={rank} size="sm" />
        </div>
      </div>
      <div className="h-2 rounded-full bg-black/40 border border-white/10 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${color}99, ${color})`, boxShadow: `0 0 8px ${color}88` }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, level))}%` }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        />
      </div>
      {note && <p className="mt-1 text-[11px] leading-snug text-white/40">{note}</p>}
    </div>
  );
}
