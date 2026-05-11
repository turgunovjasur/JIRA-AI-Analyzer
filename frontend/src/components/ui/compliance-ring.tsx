"use client";

type ComplianceRingProps = {
  score: number;
  size?: number;
};

export function ComplianceRing({ score, size = 88 }: ComplianceRingProps) {
  const color =
    score >= 80 ? "#15803d" : score >= 60 ? "#d97706" : "#b91c1c";
  const r = size * 0.43;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const dash = (score / 100) * circumference;

  return (
    <div className="compliance-ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="var(--bg-strong)"
          strokeWidth="7"
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeDasharray={`${dash} ${circumference - dash}`}
          strokeDashoffset={circumference / 4}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 800ms ease" }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dy="0.35em"
          fontSize={size * 0.2}
          fontWeight="800"
          fill={color}
          fontFamily="var(--font-display)"
        >
          {score}%
        </text>
      </svg>
      <span className="text-xs text-muted-foreground">Moslik</span>
    </div>
  );
}
