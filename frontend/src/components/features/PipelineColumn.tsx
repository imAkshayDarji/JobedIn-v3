import type { ApplicationListItem } from "@/types/application";
import { COLUMN_COLORS } from "@/types/application";
import { ApplicationCard } from "./ApplicationCard";

interface PipelineColumnProps {
  status: string;
  applications: ApplicationListItem[];
  onApplicationClick: (application: ApplicationListItem) => void;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string) => void;
}

export function PipelineColumn({
  status,
  applications,
  onApplicationClick,
  selectable = false,
  selectedIds,
  onSelect,
}: PipelineColumnProps) {
  return (
    <div
      className={`flex flex-col min-w-[280px] max-w-[320px] w-[300px] bg-gray-50 rounded-lg border-t-4 ${COLUMN_COLORS[status] || "border-t-gray-300"}`}
    >
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 capitalize">
          {status.replace(/_/g, " ")}
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
              selectable={selectable}
              selected={selectedIds?.has(app.id) ?? false}
              onSelect={() => onSelect?.(app.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
