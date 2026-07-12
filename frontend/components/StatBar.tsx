interface StatBarProps {
  label: string;
  value: number;
  /** Value range used to normalize the bar width. Defaults suit z-scored factors. */
  min?: number;
  max?: number;
}

export default function StatBar({ label, value, min = -3, max = 3 }: StatBarProps) {
  const clamped = Math.max(min, Math.min(max, value));
  const percent = ((clamped - min) / (max - min)) * 100;
  const isPositive = value >= 0;

  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-ink-secondary mb-1 font-mono">
        <span>{label}</span>
        <span className={isPositive ? "text-gold" : "text-red-400"}>
          {isPositive ? "+" : ""}
          {value.toFixed(3)}
        </span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full rounded-full ${isPositive ? "bg-gold" : "bg-red-400"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
