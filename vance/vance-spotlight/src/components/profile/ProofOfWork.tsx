import { ExternalLink } from "lucide-react";

interface ProofItem {
  company: string;
  description: string;
  impact: string;
  link?: string;
}

interface ProofOfWorkProps {
  items: ProofItem[];
}

export const ProofOfWork = ({ items }: ProofOfWorkProps) => {
  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div 
          key={index}
          className="profile-card p-5 group cursor-pointer"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h4 className="font-semibold text-foreground group-hover:text-accent transition-colors">
                {item.company}
              </h4>
              <p className="text-sm text-muted-foreground mt-1">
                {item.description}
              </p>
              <p className="text-sm text-accent font-medium mt-2">
                {item.impact}
              </p>
            </div>
            {item.link && (
              <ExternalLink className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-1" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
