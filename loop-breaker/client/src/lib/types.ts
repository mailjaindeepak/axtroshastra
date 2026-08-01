export type StatKey =
  | "STRENGTH"
  | "INTELLIGENCE"
  | "DEXTERITY"
  | "DISCIPLINE"
  | "PERSISTENCE";

export interface StatBlock {
  key: StatKey;
  label: string;
  level: number;
  note?: string;
}

export interface TrackProgress {
  key: "sql" | "ai-ml" | "dsa" | "gym";
  label: string;
  percent: number;
  path: string;
}

export interface ProfileSeed {
  name: string;
  title: string;
  synopsis: string;
  strengths: string[];
  weaknesses: string[];
  stats: StatBlock[];
}
