import Link from "next/link";
import type { ActivityItem } from "@/types/dashboard";

interface ActivityFeedProps {
  items: ActivityItem[];
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMs / 3_600_000);
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function getItemIcon(type: ActivityItem["type"]): string {
  switch (type) {
    case "application":
      return "B";
    case "resume":
      return "R";
    case "cover_letter":
      return "C";
    case "interview_session":
      return "I";
  }
}

function getItemHref(item: ActivityItem): string {
  switch (item.type) {
    case "application":
      return item.job_id ? `/jobs/${item.job_id}` : "#";
    case "resume":
      return `/resumes/${item.id}`;
    case "cover_letter":
      return `/cover-letters/${item.id}`;
    case "interview_session":
      return "/interview";
  }
}

function getStatusBadge(status: string | null): React.ReactNode {
  if (!status) return null;
  const colors: Record<string, string> = {
    saved: "bg-blue-100 text-blue-700",
    applied: "bg-green-100 text-green-700",
    generating: "bg-yellow-100 text-yellow-700",
    completed: "bg-green-100 text-green-700",
    active: "bg-blue-100 text-blue-700",
    ready: "bg-purple-100 text-purple-700",
    rejected: "bg-red-100 text-red-700",
  };
  const cls = colors[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${cls}`}
    >
      {status}
    </span>
  );
}

export function ActivityFeed({ items }: ActivityFeedProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-4">
        No recent activity yet. Start by discovering jobs!
      </p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {items.map((item) => (
        <li key={`${item.type}-${item.id}`} className="py-3">
          <Link
            href={getItemHref(item)}
            className="flex items-center gap-3 hover:bg-gray-50 -mx-2 px-2 py-1 rounded transition-colors"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600 flex-shrink-0">
              {getItemIcon(item.type)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {item.title}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {getStatusBadge(item.status)}
              <span className="text-xs text-gray-400">
                {formatRelativeTime(item.created_at)}
              </span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
