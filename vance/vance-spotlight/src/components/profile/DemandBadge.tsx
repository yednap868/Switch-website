interface DemandBadgeProps {
  isActive?: boolean;
  introCount?: number;
  days?: number;
}

export const DemandBadge = ({ isActive = false, introCount, days = 14 }: DemandBadgeProps) => {
  if (introCount && introCount > 0) {
    return (
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 text-orange-600 text-sm font-medium">
        <span>🔥</span>
        <span>In demand · {introCount} intros in {days}d</span>
      </div>
    );
  }

  if (isActive) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10 text-yellow-600 text-sm font-medium">
        <span>⚡</span>
        <span>Actively interviewing</span>
      </div>
    );
  }

  return null;
};
