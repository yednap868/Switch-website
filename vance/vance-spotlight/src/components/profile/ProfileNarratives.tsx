import { Mic } from "lucide-react";

export interface ProfileNarrativesProps {
  culture?: string;
  proudProject?: string;
  idealRole?: string;
  careerGoalPlaceholder?: string;
}

export const ProfileNarratives = ({
  culture = "One that values innovation, encourages experimentation, and treats work–life balance as a priority, not a perk.",
  proudProject = "Built a real-time collaboration tool that scaled to 50K users.",
  idealRole = "I can work on products that genuinely improve people's lives.",
  careerGoalPlaceholder = "Tap to record",
}: ProfileNarrativesProps) => {
  return (
    <section className="mt-10 space-y-4 animate-fade-in" style={{ animationDelay: "260ms" }}>
      <NarrativeCard title="My ideal company culture is..." body={culture} />
      <NarrativeCard title="The project I'm most proud of..." body={proudProject} />
      <NarrativeCard title="I'm looking for a role where..." body={idealRole} />

      <div className="profile-card px-4 py-5 sm:px-5 sm:py-6">
        <p className="text-sm font-medium text-foreground mb-3">My biggest career goal is...</p>
        <button
          type="button"
          className="mt-1 flex w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted/40 px-4 py-6 text-center"
        >
          <Mic className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">{careerGoalPlaceholder}</span>
        </button>
      </div>

      <button
        type="button"
        className="profile-card relative flex w-full items-center justify-between px-4 py-4 sm:px-5 sm:py-5"
      >
        <div className="flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-foreground text-background">
            <Mic className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">Add custom prompt</p>
            <p className="text-xs text-muted-foreground">Record your own question for founders to hear</p>
          </div>
        </div>
      </button>
    </section>
  );
};

interface NarrativeCardProps {
  title: string;
  body: string;
}

const NarrativeCard = ({ title, body }: NarrativeCardProps) => {
  return (
    <div className="profile-card px-4 py-5 sm:px-5 sm:py-6">
      <p className="text-sm font-medium text-muted-foreground mb-2">{title}</p>
      <p className="text-base leading-relaxed text-foreground">{body}</p>
    </div>
  );
};



