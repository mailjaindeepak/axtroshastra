import { useState } from "react";

export default function PortraitPanel({
  src,
  alt,
  initial,
}: {
  src: string;
  alt: string;
  initial: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div className="relative h-[420px] md:h-[560px] lg:h-full lg:min-h-[720px] w-full overflow-hidden rounded-lg border border-gold/15">
      {!failed ? (
        <img
          src={src}
          alt={alt}
          onError={() => setFailed(true)}
          className="h-full w-full object-cover object-top"
        />
      ) : (
        <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-plum-light via-navy to-void">
          <span className="font-display text-8xl text-gold/30">{initial}</span>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-void via-void/10 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-void/70 via-transparent to-transparent lg:from-void/40" />
    </div>
  );
}
