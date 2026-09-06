interface StatCardProps {
  label: string;
  value: string;
  sublabel?: string;
  tone?: "default" | "positive" | "negative";
}

export function StatCard({ label, value, sublabel, tone = "default" }: StatCardProps) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {sublabel && <span className="stat-card__sublabel">{sublabel}</span>}
    </div>
  );
}
