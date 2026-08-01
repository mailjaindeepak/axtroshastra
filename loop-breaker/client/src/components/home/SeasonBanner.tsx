import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";

export default function SeasonBanner({
  seasonLabel,
  headline,
}: {
  seasonLabel: string;
  headline: string;
}) {
  const [dismissed, setDismissed] = useState(false);
  const navigate = useNavigate();

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.5 }}
          className="relative mx-4 md:mx-8 mt-4 rounded-lg border border-gold/30 px-5 py-4 flex items-center justify-between gap-4"
          style={{
            background: "linear-gradient(90deg, rgba(217,180,92,0.14), rgba(95,216,224,0.08))",
            boxShadow: "0 0 24px rgba(217,180,92,0.15)",
          }}
        >
          <button
            onClick={() => navigate("/episodes")}
            className="text-left flex-1"
          >
            <span className="font-display text-[11px] tracking-[0.3em] uppercase text-gold-bright text-glow-gold">
              {seasonLabel} Recap Ready
            </span>
            <p className="font-body text-sm text-white/75 mt-0.5">{headline}</p>
          </button>
          <button
            onClick={() => setDismissed(true)}
            aria-label="Dismiss"
            className="font-display text-white/40 hover:text-white/80 text-lg leading-none px-2"
          >
            &times;
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
