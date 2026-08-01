import Callout from "../ui/Callout";

export default function CriticSummary({ text }: { text: string }) {
  return <Callout eyebrow="Critic's Summary">{text}</Callout>;
}
