import { RANK_COLOR, type RankLetter } from "../../lib/rank";

export default function RankBadge({
  rank,
  size = "md",
}: {
  rank: RankLetter;
  size?: "sm" | "md" | "lg";
}) {
  const color = RANK_COLOR[rank];
  const sizeClasses =
    size === "lg" ? "w-14 h-14 text-2xl" : size === "sm" ? "w-6 h-6 text-[11px]" : "w-9 h-9 text-base";

  return (
    <div
      className={`flex items-center justify-center rounded-sm font-display font-semibold ${sizeClasses}`}
      style={{
        color,
        border: `1px solid ${color}`,
        boxShadow: `0 0 10px ${color}66, inset 0 0 8px ${color}22`,
        background: "rgba(6,6,17,0.6)",
      }}
    >
      {rank}
    </div>
  );
}
