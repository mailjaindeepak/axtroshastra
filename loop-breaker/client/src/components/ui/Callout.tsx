import type { ReactNode } from "react";

export default function Callout({
  eyebrow,
  children,
}: {
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <div className="panel-glass rounded-lg p-5 relative">
      <span className="absolute -top-3 left-4 px-2 bg-navy font-display text-[11px] tracking-[0.25em] uppercase text-gold-bright text-glow-gold">
        {eyebrow}
      </span>
      <p className="font-body italic text-[14px] leading-relaxed text-white/75">{children}</p>
    </div>
  );
}
