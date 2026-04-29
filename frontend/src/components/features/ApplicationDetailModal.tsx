"use client";

import { useState } from "react";
import {
  X,
  MapPin,
  Banknote,
  Clock,
  FileText,
  BookOpen,
  MessageSquare,
  Trash2,
  ExternalLink,
  Save,
} from "lucide-react";
import type { ApplicationDetail, ApplicationStatus } from "@/types/application";
import { updateApplication, updateApplicationNotes, deleteApplication } from "@/lib/api/applications";

interface ApplicationDetailModalProps {
  application: ApplicationDetail;
  onClose: () => void;
  onUpdated: () => void;
  onDeleted: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  saved: "bg-gray-100 text-gray-700",
  generating: "bg-yellow-100 text-yellow-800",
  ready: "bg-blue-100 text-blue-800",
  applied: "bg-indigo-100 text-indigo-800",
  screening: "bg-purple-100 text-purple-800",
  interview: "bg-cyan-100 text-cyan-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-500",
};

const NEXT_STATUSES: Record<string, ApplicationStatus[]> = {
  saved: ["generating", "withdrawn"],
  generating: ["ready", "rejected"],
  ready: ["applied", "withdrawn"],
  applied: ["screening", "rejected", "withdrawn"],
  screening: ["interview", "rejected", "withdrawn"],
  interview: ["offer", "rejected", "withdrawn"],
  offer: ["withdrawn"],
  rejected: [],
  withdrawn: [],
};

export function ApplicationDetailModal({
  application,
  onClose,
  onUpdated,
  onDeleted,
}: ApplicationDetailModalProps) {
  const [notes, setNotes] = useState(application.notes ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const nextStatuses = NEXT_STATUSES[application.status] ?? [];

  async function handleStatusUpdate(newStatus: ApplicationStatus) {
    setIsSaving(true);
    try {
      await updateApplication(application.id, { status: newStatus });
      onUpdated();
    } catch {
      // error handled by parent refresh
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveNotes() {
    setIsSaving(true);
    try {
      await updateApplicationNotes(application.id, notes);
      onUpdated();
    } catch {
      // error handled by parent refresh
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete() {
    setIsDeleting(true);
    try {
      await deleteApplication(application.id);
      onDeleted();
    } catch {
      // error handled by parent
    } finally {
      setIsDeleting(false);
    }
  }

  const { job } = application;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{job.title}</h2>
            <p className="text-sm text-gray-600">{job.company}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-5">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium capitalize ${STATUS_STYLES[application.status] || "bg-gray-100 text-gray-700"}`}
            >
              {application.status}
            </span>
            {application.applied_at && (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                Applied {new Date(application.applied_at).toLocaleDateString()}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            {job.location && (
              <div className="flex items-center gap-2 text-gray-600">
                <MapPin className="w-4 h-4 text-gray-400" />
                {job.location}
              </div>
            )}
            {job.salary_min != null && job.salary_max != null && (
              <div className="flex items-center gap-2 text-gray-600">
                <Banknote className="w-4 h-4 text-gray-400" />$
                {job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}
              </div>
            )}
            {job.remote_policy && (
              <div className="text-gray-600 capitalize">
                {job.remote_policy}
              </div>
            )}
            {application.match_score != null && (
              <div className="text-gray-600">
                Match: {Math.round(application.match_score)}%
              </div>
            )}
          </div>

          {nextStatuses.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                Move to
              </h3>
              <div className="flex flex-wrap gap-2">
                {nextStatuses.map((s) => (
                  <button
                    key={s}
                    type="button"
                    disabled={isSaving}
                    onClick={() => handleStatusUpdate(s)}
                    className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-medium capitalize transition-colors ${STATUS_STYLES[s] || "bg-gray-100 text-gray-700"} hover:opacity-80 disabled:opacity-50`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            {application.resume_id ? (
              <a
                href={`/resumes/${application.resume_id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                View Resume
              </a>
            ) : (
              <a
                href={`/resumes?jobId=${job.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                Generate Resume
              </a>
            )}
            {application.cover_letter_id ? (
              <a
                href={`/cover-letters/${application.cover_letter_id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100 transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                View Cover Letter
              </a>
            ) : (
              <a
                href={`/cover-letters?jobId=${job.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                Generate Cover Letter
              </a>
            )}
            {application.interview_prep_id ? (
              <a
                href={`/interview-prep/${application.interview_prep_id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-purple-200 bg-purple-50 px-3 py-1.5 text-xs font-medium text-purple-700 hover:bg-purple-100 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                View Interview Prep
              </a>
            ) : (
              <a
                href={`/interview-prep?jobId=${job.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Generate Interview Prep
              </a>
            )}
            {job.source_url && (
              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Source
              </a>
            )}
          </div>

          <div>
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Notes
            </h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes about this application..."
              rows={3}
              maxLength={2000}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
            <div className="flex items-center justify-between mt-1.5">
              <span className="text-[10px] text-gray-400">
                {notes.length}/2000
              </span>
              <button
                type="button"
                onClick={handleSaveNotes}
                disabled={isSaving}
                className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                <Save className="w-3 h-3" />
                Save
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <p className="text-[10px] text-gray-400">
              Created {new Date(application.created_at).toLocaleDateString()}
              {" "}&middot;{" "}
              Updated {new Date(application.updated_at).toLocaleDateString()}
            </p>
            <div>
              {showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(false)}
                    className="rounded-lg border border-gray-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="inline-flex items-center gap-1 rounded-lg bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
                    Confirm Delete
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                  Delete
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
