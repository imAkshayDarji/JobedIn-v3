"use client";

import { Check, Loader2 } from "lucide-react";
import type { ApplyStep } from "@/types/apply";
import { APPLY_STEP_LABELS, APPLY_STEPS } from "@/types/apply";

interface ApplyStepProgressProps {
  completedSteps: Set<string>;
  currentStep: string | null;
}

export function ApplyStepProgress({ completedSteps, currentStep }: ApplyStepProgressProps) {
  return (
    <div className="space-y-2">
      {APPLY_STEPS.map((step) => {
        const isCompleted = completedSteps.has(step);
        const isCurrent = currentStep === step;

        return (
          <div key={step} className="flex items-center gap-3">
            <div className="flex-shrink-0">
              {isCompleted ? (
                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-green-600" />
                </div>
              ) : isCurrent ? (
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                  <Loader2 className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                </div>
              ) : (
                <div className="w-6 h-6 rounded-full border-2 border-gray-200" />
              )}
            </div>
            <span
              className={`text-sm ${
                isCompleted
                  ? "text-green-700 font-medium"
                  : isCurrent
                    ? "text-blue-700 font-medium"
                    : "text-gray-400"
              }`}
            >
              {APPLY_STEP_LABELS[step as ApplyStep]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
