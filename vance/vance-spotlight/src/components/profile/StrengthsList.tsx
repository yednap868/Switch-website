import { Check, Play } from "lucide-react";
import { useState } from "react";

interface Strength {
  text: string;
  hasAudio?: boolean;
}

interface StrengthsListProps {
  strengths: Strength[];
}

export const StrengthsList = ({ strengths }: StrengthsListProps) => {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);

  return (
    <ul className="space-y-3">
      {strengths.map((strength, index) => (
        <li 
          key={index}
          className="flex items-center gap-3 group"
        >
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent/10 text-accent flex-shrink-0">
            <Check className="w-3.5 h-3.5" />
          </span>
          <span className="text-foreground flex-1">{strength.text}</span>
          {strength.hasAudio && (
            <button
              onClick={() => setPlayingIndex(playingIndex === index ? null : index)}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-2 rounded-full hover:bg-secondary"
              aria-label="Play audio"
            >
              <Play className="w-4 h-4 text-muted-foreground" />
            </button>
          )}
        </li>
      ))}
    </ul>
  );
};
