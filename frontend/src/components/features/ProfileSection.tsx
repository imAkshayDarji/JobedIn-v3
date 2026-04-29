"use client";

import { ReactNode } from "react";

interface ProfileSectionProps {
  title: string;
  icon?: ReactNode;
  onAdd?: () => void;
  isLoading?: boolean;
  error?: string | null;
  children: ReactNode;
}

export function ProfileSection({
  title,
  icon,
  onAdd,
  isLoading,
  error,
  children,
}: ProfileSectionProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon && <span className="text-gray-400">{icon}</span>}
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        {onAdd && (
          <button
            type="button"
            onClick={onAdd}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            + Add
          </button>
        )}
      </div>

      {isLoading && (
        <div className="space-y-2">
          <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200" />
        </div>
      )}

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!isLoading && !error && children}
    </div>
  );
}
