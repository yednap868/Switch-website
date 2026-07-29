import { BadgeCheck, Shield } from "lucide-react";

interface VanceBadgeProps {
  verifiedDate: string;
  score?: number;
  percentile?: number;
}

export const VanceBadge = ({ verifiedDate, score, percentile = 100 }: VanceBadgeProps) => {
  // Only show badge if profile exists (score > 0 or percentile > 0)
  if (!score && !percentile) {
    return null;
  }
  
  // Use default values if not provided
  const displayScore = score || 100;
  const displayPercentile = percentile || 100;
  
  return (
    <div className="profile-card p-6 bg-gradient-to-br from-verification/5 to-transparent border-verification/20">
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-verification/10">
          <Shield className="w-6 h-6 text-verification" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-foreground">✅ Vance Verified 100%</h4>
            <BadgeCheck className="w-5 h-5 text-verification" />
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            This profile has been verified by the Vance team through skill checks, background verification, and references.
          </p>
          {verifiedDate && (
            <div className="flex items-center gap-6 mt-4">
              <div>
                <span className="text-xs text-muted-foreground">Verified:</span>
                <p className="text-sm font-medium text-foreground">{verifiedDate}</p>
              </div>
              {displayScore > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground">Verification score:</span>
                  <p className="text-sm font-medium text-verification">{displayScore} / 100</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
