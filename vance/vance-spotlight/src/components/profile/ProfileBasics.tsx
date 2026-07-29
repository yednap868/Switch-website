import { Briefcase, DollarSign, MapPin } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type WorkArrangementOption = "remote" | "hybrid" | "onsite" | "flexible";
type SalaryRangeOption =
  | "150k-180k"
  | "180k-220k"
  | "220k-260k"
  | "260k-300k"
  | "300k-plus";
type RelocationOption = "not-open" | "open" | "open-us" | "open-remote-hubs";

export interface ProfileBasicsProps {
  workArrangement?: WorkArrangementOption;
  salaryRange?: SalaryRangeOption;
  relocation?: RelocationOption;
}

export const ProfileBasics = ({
  workArrangement = "hybrid",
  salaryRange = "220k-260k",
  relocation = "not-open",
}: ProfileBasicsProps) => {
  return (
    <section className="mt-8 animate-fade-in" style={{ animationDelay: "120ms" }}>
      <h2 className="text-lg font-semibold mb-3">Basics</h2>
      <div className="profile-card divide-y divide-border">
        <div className="flex items-center justify-between px-4 py-3 sm:px-5 sm:py-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
              <Briefcase className="h-4 w-4 text-foreground" />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">Work Arrangement</p>
              <p className="text-xs text-muted-foreground">How you prefer to work day‑to‑day</p>
            </div>
          </div>
          <div className="w-40">
            <Select defaultValue={workArrangement}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="remote">Remote</SelectItem>
                <SelectItem value="hybrid">Hybrid / Remote</SelectItem>
                <SelectItem value="onsite">On‑site</SelectItem>
                <SelectItem value="flexible">Flexible</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 sm:px-5 sm:py-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
              <DollarSign className="h-4 w-4 text-foreground" />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">Salary Range</p>
              <p className="text-xs text-muted-foreground">Total annual cash you&apos;re targeting</p>
            </div>
          </div>
          <div className="w-40">
            <Select defaultValue={salaryRange}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="150k-180k">$150k – $180k</SelectItem>
                <SelectItem value="180k-220k">$180k – $220k</SelectItem>
                <SelectItem value="220k-260k">$220k – $260k</SelectItem>
                <SelectItem value="260k-300k">$260k – $300k</SelectItem>
                <SelectItem value="300k-plus">$300k+</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 sm:px-5 sm:py-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
              <MapPin className="h-4 w-4 text-foreground" />
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">Open to relocate</p>
              <p className="text-xs text-muted-foreground">Where you&apos;re willing to move</p>
            </div>
          </div>
          <div className="w-40">
            <Select defaultValue={relocation}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="not-open">Not open</SelectItem>
                <SelectItem value="open">Open to relocate</SelectItem>
                <SelectItem value="open-us">Open within US</SelectItem>
                <SelectItem value="open-remote-hubs">Open to major tech hubs</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </section>
  );
};



