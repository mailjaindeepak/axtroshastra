import { useNavigate } from "react-router-dom";
import type { TrackProgress } from "../../lib/types";
import ProgressBar from "../ui/ProgressBar";
import Divider from "../ui/Divider";

export default function ProgressPanel({ tracks }: { tracks: TrackProgress[] }) {
  const navigate = useNavigate();
  const total = Math.round(tracks.reduce((sum, t) => sum + t.percent, 0) / tracks.length);

  return (
    <div className="panel-glass rounded-lg p-5 md:p-6">
      <h2 className="font-display text-sm tracking-[0.3em] uppercase text-gold-bright text-glow-gold mb-1">
        Total Progress
      </h2>
      <Divider variant="gold" />
      <div className="mt-5 mb-6">
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-display text-[13px] tracking-[0.15em] uppercase text-white/75">
            All Tracks
          </span>
          <span className="font-mono text-sm text-white/70">{total}%</span>
        </div>
        <ProgressBar percent={total} color="var(--color-gold)" height={10} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        {tracks.map((track) => (
          <button
            key={track.key}
            onClick={() => navigate(track.path)}
            className="text-left group"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-display text-[11px] tracking-[0.15em] uppercase text-white/55 group-hover:text-cyan-bright transition-colors">
                {track.label}
              </span>
              <span className="font-mono text-[11px] text-white/45">{track.percent}%</span>
            </div>
            <ProgressBar percent={track.percent} color="var(--color-cyan)" height={5} />
          </button>
        ))}
      </div>
    </div>
  );
}
