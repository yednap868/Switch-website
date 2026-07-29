import { Quote } from "lucide-react";

interface ThoughtCardProps {
  content: string;
  topic?: string;
}

export const ThoughtCard = ({ content, topic }: ThoughtCardProps) => {
  return (
    <div className="profile-card p-6 relative overflow-hidden">
      <Quote className="absolute top-4 right-4 w-8 h-8 text-accent/10" />
      {topic && (
        <span className="inline-block px-3 py-1 text-xs font-medium bg-highlight text-accent rounded-full mb-3">
          {topic}
        </span>
      )}
      <p className="text-foreground leading-relaxed relative z-10">
        "{content}"
      </p>
    </div>
  );
};
