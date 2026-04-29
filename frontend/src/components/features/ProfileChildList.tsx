"use client";

import { ReactNode } from "react";

interface ProfileChildListProps<T> {
  items: T[];
  renderItem: (item: T) => ReactNode;
  onAdd?: () => void;
  onEdit?: (item: T) => void;
  onDelete?: (item: T) => void;
  isLoading?: boolean;
  entityName: string;
  emptyMessage?: string;
}

export function ProfileChildList<T extends { id: string }>({
  items,
  renderItem,
  onAdd,
  onEdit,
  onDelete,
  isLoading,
  entityName,
  emptyMessage,
}: ProfileChildListProps<T>) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-md bg-gray-100"
          />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="py-4 text-center">
        <p className="text-sm text-gray-500">
          {emptyMessage ?? `No ${entityName} added yet.`}
        </p>
        {onAdd && (
          <button
            type="button"
            onClick={onAdd}
            className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            + Add {entityName}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.id}
          className="group flex items-start justify-between rounded-md border border-gray-100 p-3 hover:bg-gray-50 transition-colors"
        >
          <div className="flex-1 min-w-0">{renderItem(item)}</div>
          <div className="ml-2 flex shrink-0 gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {onEdit && (
              <button
                type="button"
                onClick={() => onEdit(item)}
                className="rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200 transition-colors"
              >
                Edit
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={() => onDelete(item)}
                className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
              >
                Delete
              </button>
            )}
          </div>
        </div>
      ))}
      {onAdd && (
        <button
          type="button"
          onClick={onAdd}
          className="w-full rounded-md border border-dashed border-gray-300 py-2 text-sm font-medium text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
        >
          + Add {entityName}
        </button>
      )}
    </div>
  );
}
