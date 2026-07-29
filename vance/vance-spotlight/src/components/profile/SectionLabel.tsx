interface SectionLabelProps {
  children: React.ReactNode;
  emoji?: string;
}
export const SectionLabel = ({
  children,
  emoji
}: SectionLabelProps) => {
  return <h3 className="section-label flex items-center gap-2 mb-4 font-mono">
      {emoji && <span>{emoji}</span>}
      {children}
    </h3>;
};