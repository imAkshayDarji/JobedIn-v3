import type { ApplicationListItem } from "@/types/application";
import { ApplicationCard } from "./ApplicationCard";

interface PipelineColumnProps {
  status: string;
  applications: ApplicationListItem[];
  onApplicationClick: (application: ApplicationListItem) => void;
}

const COLUMN_COLORS: Record<string, string> = {
  saved: "border-t-gray-400",
  generating: "border-t-yellow-400",
  ready: "border-t-blue-400",
  applied: "border-t-indigo-400",
  screening: "border-t-purple-400",
  interview: "border-t-cyan-400",
  offer: "border-t-green-400",
  rejected: "border-t-red-400",
  withdrawn: "border-t-gray-300",
};

export function PipelineColumn({
  status,
  applications,
  onApplicationClick,
}: PipelineColumnProps) {
  return (
    <div
      className={`flex flex-col min-w-[280px] max-w-[320px] w-[300px] bg-gray-50 rounded-lg border-t-4 ${COLUMN_COLORS[status] || "border-t-gray-300"}`}
    >
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 capitalize">
          {status}
        </h3>
        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white border border-gray-200 text-xs font-medium text-gray-600">
          {applications.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2 max-h-[calc(100vh-220px)]">
        {applications.length === 0 ? (
          <div className="flex items-center justify-center py-8 px-2">
            <p className="text-xs text-gray-400 text-center">
              No applications in this stage
            </p>
          </div>
        ) : (
          applications.map((app) => (
            <ApplicationCard
              key={app.id}
              application={app}
              onClick={() => onApplicationClick(app)}
            />
          ))
        )}
      </div>
    </div>
  );
}
