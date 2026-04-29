import Link from "next/link";

interface StatCardProps {
  label: string;
  value: string | number | null;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: "blue" | "green" | "yellow" | "purple" | "red" | "gray" | "teal";
  progress?: number;
  href?: string;
}

const colorMap: Record<string, string> = {
  blue: "border-blue-500 bg-blue-50",
  green: "border-green-500 bg-green-50",
  yellow: "border-yellow-500 bg-yellow-50",
  purple: "border-purple-500 bg-purple-50",
  red: "border-red-500 bg-red-50",
  gray: "border-gray-400 bg-gray-50",
  teal: "border-teal-500 bg-teal-50",
};

const progressColorMap: Record<string, string> = {
  blue: "bg-blue-500",
  green: "bg-green-500",
  yellow: "bg-yellow-500",
  purple: "bg-purple-500",
  red: "bg-red-500",
  gray: "bg-gray-400",
  teal: "bg-teal-500",
};

export function StatCard({
  label,
  value,
  subtitle,
  icon,
  color = "blue",
  progress,
  href,
}: StatCardProps) {
  const displayValue = value === null ? "--" : value;
  const borderBg = colorMap[color] ?? colorMap.blue;
  const progressColor = progressColorMap[color] ?? progressColorMap.blue;

  const content = (
    <div
      className={`rounded-lg border-l-4 ${borderBg} p-4 hover:shadow-sm transition-shadow ${
        href ? "cursor-pointer" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-2xl font-bold text-gray-900">{displayValue}</p>
          <p className="text-sm font-medium text-gray-600 mt-0.5">{label}</p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
          )}
        </div>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      {progress != null && (
        <div className="mt-3 h-1.5 w-full rounded-full bg-gray-200">
          <div
            className={`h-1.5 rounded-full ${progressColor} transition-all`}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }

  return content;
}
