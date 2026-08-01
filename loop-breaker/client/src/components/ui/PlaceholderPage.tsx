import PageShell from "../layout/PageShell";

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <PageShell>
      <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3 px-4 text-center">
        <h1 className="font-display text-2xl tracking-[0.2em] uppercase text-gold-bright text-glow-gold">
          {title}
        </h1>
        <p className="font-body text-sm text-white/40 max-w-md">
          Layout pending — built after the Home page art direction is approved.
        </p>
      </div>
    </PageShell>
  );
}
