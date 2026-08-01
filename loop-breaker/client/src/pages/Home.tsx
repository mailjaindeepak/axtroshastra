import { motion } from "framer-motion";
import PageShell from "../components/layout/PageShell";
import PortraitPanel from "../components/home/PortraitPanel";
import StatsPanel from "../components/home/StatsPanel";
import GrowthPanel from "../components/home/GrowthPanel";
import ProgressPanel from "../components/home/ProgressPanel";
import CriticSummary from "../components/home/CriticSummary";
import SeasonBanner from "../components/home/SeasonBanner";
import Divider from "../components/ui/Divider";
import RankBadge from "../components/ui/RankBadge";
import { rankForLevel } from "../lib/rank";
import { PROFILE_SEED, TRACK_PROGRESS_SEED, CRITIC_SUMMARY_SEED } from "../data/seed";

// Mock 30-days-ago snapshot for layout purposes only — replaced by a real
// stored snapshot once the backend exists.
const GROWTH_ROWS = PROFILE_SEED.stats.map((s) => ({
  ...s,
  levelThirtyDaysAgo: Math.max(0, s.level - [4, 6, 2, 9, 3][PROFILE_SEED.stats.indexOf(s)]),
}));

const overallLevel = Math.round(
  PROFILE_SEED.stats.reduce((sum, s) => sum + s.level, 0) / PROFILE_SEED.stats.length
);

export default function Home() {
  return (
    <PageShell>
      <SeasonBanner
        seasonLabel="Season 1"
        headline="14 episodes in, rolling average up 1.6 — the recap is ready to view."
      />

      {/* Hero: portrait + identity */}
      <section className="grid lg:grid-cols-[minmax(0,420px)_1fr] gap-8 px-4 md:px-8 pt-8">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <PortraitPanel src="/portrait/home.jpg" alt={PROFILE_SEED.name} initial="S" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex flex-col justify-center"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RankBadge rank={rankForLevel(overallLevel)} size="lg" />
              <div>
                <p className="font-mono text-[11px] tracking-[0.2em] uppercase text-cyan-bright/80">
                  Rising Hunter
                </p>
                <h1 className="font-display text-3xl md:text-4xl tracking-wide text-white text-glow-gold">
                  {PROFILE_SEED.name}
                </h1>
              </div>
            </div>
            <div className="hidden md:flex flex-col items-end">
              <span className="font-display text-xs tracking-[0.35em] uppercase text-gold-bright text-glow-gold">
                About &#8250;
              </span>
              <span className="font-mono text-[10px] text-white/30 mt-1">profile.sys</span>
            </div>
          </div>

          <p className="font-display text-sm md:text-base tracking-[0.05em] text-cyan-bright/90 mt-1">
            {PROFILE_SEED.title}
          </p>

          <div className="mt-4">
            <Divider variant="gold" />
          </div>

          <p className="font-body text-[15px] leading-relaxed text-white/70 mt-5 max-w-2xl">
            {PROFILE_SEED.synopsis}
          </p>

          <div className="grid sm:grid-cols-2 gap-6 mt-7">
            <div>
              <h3 className="font-display text-[12px] tracking-[0.25em] uppercase text-gold-bright mb-2">
                Strengths
              </h3>
              <ul className="flex flex-col gap-1.5">
                {PROFILE_SEED.strengths.map((s) => (
                  <li key={s} className="text-[12.5px] leading-snug text-white/60 flex gap-2">
                    <span className="text-gold/60 shrink-0">&#10094;</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="font-display text-[12px] tracking-[0.25em] uppercase text-cyan-bright mb-2">
                Weaknesses
              </h3>
              <ul className="flex flex-col gap-1.5">
                {PROFILE_SEED.weaknesses.map((w) => (
                  <li key={w} className="text-[12.5px] leading-snug text-white/60 flex gap-2">
                    <span className="text-cyan/60 shrink-0">&#10094;</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Stats + Growth + Progress + Critic */}
      <section className="grid lg:grid-cols-2 gap-6 px-4 md:px-8 py-10">
        <div className="flex flex-col gap-6">
          <StatsPanel stats={PROFILE_SEED.stats} />
          <GrowthPanel rows={GROWTH_ROWS} baselineLabel="30 days ago" />
        </div>
        <div className="flex flex-col gap-6">
          <ProgressPanel tracks={TRACK_PROGRESS_SEED} />
          <CriticSummary text={CRITIC_SUMMARY_SEED} />
        </div>
      </section>
    </PageShell>
  );
}
