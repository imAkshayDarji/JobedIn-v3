"use client";

interface DifficultyIndicatorProps {
  difficulty: number;
}

const LABELS: Record<number, string> = {
  1: "Basic",
  2: "Intermediate",
  3: "Advanced",
};

const COLORS: Record<number, string> = {
  1: "bg-green-100 text-green-700 border-green-200",
  2: "bg-yellow-100 text-yellow-700 border-yellow-200",
  3: "bg-red-100 text-red-700 border-red-200",
};

const DOT_COLORS: Record<number, string> = {
  1: "bg-green-500",
  2: "bg-yellow-500",
  3: "bg-red-500",
};

export function DifficultyIndicator({ difficulty }: DifficultyIndicatorProps) {
  const label = LABELS[difficulty] || "Unknown";
  const colorClasses = COLORS[difficulty] || COLORS[1];
  const dotColor = DOT_COLORS[difficulty] || DOT_COLORS[1];

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${colorClasses}`}>
      <div className={`w-2 h-2 rounded-full ${dotColor}`} />
      {label}
    </div>
  );
}
