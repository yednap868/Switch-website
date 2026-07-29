import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface ProfileSkillsProps {
  skills?: string[];
}

export const ProfileSkills = ({ skills = [] }: ProfileSkillsProps) => {
  const defaultSkills =
    skills.length > 0
      ? skills
      : ["Python", "React", "TypeScript", "Node.js", "PostgreSQL", "AWS", "Docker", "GraphQL"];

  return (
    <section className="mt-8 animate-fade-in" style={{ animationDelay: "180ms" }}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Skills</h2>
        <Button variant="ghost" size="sm" className="gap-1 text-xs font-medium">
          <Plus className="h-3 w-3" />
          Add
        </Button>
      </div>
      <div className="profile-card px-4 py-3 sm:px-5 sm:py-4">
        <div className="flex flex-wrap gap-2">
          {defaultSkills.map((skill) => (
            <Badge
              key={skill}
              variant="secondary"
              className="rounded-full px-3 py-1 text-xs font-medium bg-secondary text-foreground"
            >
              {skill}
            </Badge>
          ))}
        </div>
      </div>
    </section>
  );
};



