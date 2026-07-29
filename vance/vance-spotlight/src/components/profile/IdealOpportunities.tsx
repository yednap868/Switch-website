import { Briefcase, Building2, Target } from "lucide-react";

interface OpportunitiesProps {
  role: string;
  industries: string[];
  companyStage: string;
}

export const IdealOpportunities = ({ role, industries, companyStage }: OpportunitiesProps) => {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="profile-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-lg bg-accent/10">
            <Briefcase className="w-4 h-4 text-accent" />
          </div>
          <span className="text-sm font-medium text-muted-foreground">Role</span>
        </div>
        <p className="font-medium text-foreground">{role}</p>
      </div>
      
      <div className="profile-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-lg bg-accent/10">
            <Building2 className="w-4 h-4 text-accent" />
          </div>
          <span className="text-sm font-medium text-muted-foreground">Industry</span>
        </div>
        <p className="font-medium text-foreground">{industries.join(" · ")}</p>
      </div>
      
      <div className="profile-card p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 rounded-lg bg-accent/10">
            <Target className="w-4 h-4 text-accent" />
          </div>
          <span className="text-sm font-medium text-muted-foreground">Stage</span>
        </div>
        <p className="font-medium text-foreground">{companyStage}</p>
      </div>
    </div>
  );
};
