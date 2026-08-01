export type RankLetter = "E" | "D" | "C" | "B" | "A" | "S";

const RANK_THRESHOLDS: { min: number; rank: RankLetter }[] = [
  { min: 96, rank: "S" },
  { min: 81, rank: "A" },
  { min: 61, rank: "B" },
  { min: 41, rank: "C" },
  { min: 21, rank: "D" },
  { min: 0, rank: "E" },
];

/** E: 0-20 · D: 21-40 · C: 41-60 · B: 61-80 · A: 81-95 · S: 96-100 */
export function rankForLevel(level: number): RankLetter {
  const clamped = Math.max(0, Math.min(100, level));
  return RANK_THRESHOLDS.find((t) => clamped >= t.min)!.rank;
}

export const RANK_COLOR: Record<RankLetter, string> = {
  E: "var(--color-rank-e)",
  D: "var(--color-rank-d)",
  C: "var(--color-rank-c)",
  B: "var(--color-rank-b)",
  A: "var(--color-rank-a)",
  S: "var(--color-rank-s)",
};
