interface ActivityCardProps {
  introductions: number;
  interviewsScheduled: number;
  avgResponseTime: string;
}

export const ActivityCard = ({ introductions, interviewsScheduled, avgResponseTime }: ActivityCardProps) => {
  return (
    <div className="profile-card p-5 bg-gradient-to-br from-accent/5 to-transparent">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">🚀</span>
        <h4 className="font-semibold text-foreground">Vance activity</h4>
      </div>
      <ul className="space-y-2 text-sm">
        <li className="flex items-center gap-2 text-muted-foreground">
          <span className="text-foreground">•</span>
          Introduced to <span className="font-medium text-foreground">{introductions}</span> relevant founders
        </li>
        <li className="flex items-center gap-2 text-muted-foreground">
          <span className="text-foreground">•</span>
          <span className="font-medium text-foreground">{interviewsScheduled}</span> interviews scheduled
        </li>
        <li className="flex items-center gap-2 text-muted-foreground">
          <span className="text-foreground">•</span>
          Avg response time: <span className="font-medium text-foreground">{avgResponseTime}</span>
        </li>
      </ul>
    </div>
  );
};
