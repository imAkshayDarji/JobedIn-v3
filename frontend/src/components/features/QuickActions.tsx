import Link from "next/link";

const actions = [
  {
    label: "Discover Jobs",
    href: "/jobs",
    color: "bg-blue-600 text-white hover:bg-blue-700",
  },
  {
    label: "Generate Resume",
    href: "/resumes/generate",
    color: "bg-purple-600 text-white hover:bg-purple-700",
  },
  {
    label: "Cover Letter",
    href: "/cover-letters/generate",
    color: "bg-teal-600 text-white hover:bg-teal-700",
  },
  {
    label: "Interview Coach",
    href: "/interview",
    color: "bg-orange-600 text-white hover:bg-orange-700",
  },
];

export function QuickActions() {
  return (
    <div className="flex flex-wrap gap-3">
      {actions.map((action) => (
        <Link
          key={action.href}
          href={action.href}
          className={`inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${action.color}`}
        >
          {action.label}
        </Link>
      ))}
    </div>
  );
}
