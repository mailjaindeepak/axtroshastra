export default function Divider({ variant = "gold" }: { variant?: "gold" | "cyan" }) {
  return <div className={variant === "gold" ? "divider-gold" : "divider-cyan"} />;
}
