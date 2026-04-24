"use client";

import { Pencil } from "lucide-react";

import type {
  OnboardingSaveRequest,
  PersonalInfo,
  TargetRole,
  Skill,
  Education,
  Experience,
} from "@/types/onboarding";

interface ReviewConfirmProps {
  data: OnboardingSaveRequest;
  onEditStep: (step: number) => void;
  onSubmit: () => void;
  loading: boolean;
}

function Section({
  title,
  onEdit,
  step,
  children,
}: {
  title: string;
  onEdit: () => void;
  step: number;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">{title}</h4>
        <button
          type="button"
          onClick={onEdit}
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
        >
          <Pencil className="h-3.5 w-3.5" />
          Edit
        </button>
      </div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function FieldRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex text-sm">
      <span className="w-32 flex-shrink-0 text-gray-500">{label}</span>
      <span className="text-gray-900">{value}</span>
    </div>
  );
}

export function ReviewConfirm({
  data,
  onEditStep,
  onSubmit,
  loading,
}: ReviewConfirmProps) {
  const pi = data.personal_info;

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Review your information below before submitting. Click &quot;Edit&quot;
        on any section to make changes.
      </p>

      <Section title="Personal Details" onEdit={() => onEditStep(2)} step={2}>
        <div className="space-y-1">
          <FieldRow label="Name" value={`${pi.first_name} ${pi.last_name}`} />
          <FieldRow label="Headline" value={pi.headline} />
          <FieldRow label="Location" value={pi.location} />
          <FieldRow label="Phone" value={pi.phone} />
          <FieldRow label="Level" value={pi.experience_level} />
          {pi.summary && (
            <div className="mt-2 text-sm">
              <span className="text-gray-500">Summary:</span>
              <p className="mt-1 whitespace-pre-wrap text-gray-700">
                {pi.summary}
              </p>
            </div>
          )}
        </div>
      </Section>

      <Section title="Target Roles" onEdit={() => onEditStep(2)} step={2}>
        {data.target_roles.length === 0 ? (
          <p className="text-sm text-gray-500">No target roles added</p>
        ) : (
          <ul className="space-y-1">
            {data.target_roles.map((role: TargetRole, i: number) => (
              <li key={i} className="text-sm text-gray-700">
                {role.title}
                {role.keywords && (
                  <span className="ml-2 text-gray-400">({role.keywords})</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Skills" onEdit={() => onEditStep(3)} step={3}>
        {data.skills.length === 0 ? (
          <p className="text-sm text-gray-500">No skills added</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {data.skills.map((skill: Skill, i: number) => (
              <span
                key={i}
                className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700"
              >
                {skill.name}
                {skill.proficiency && (
                  <span className="ml-1 text-blue-400">
                    ({skill.proficiency})
                  </span>
                )}
              </span>
            ))}
          </div>
        )}
      </Section>

      <Section title="Education" onEdit={() => onEditStep(4)} step={4}>
        {data.education.length === 0 ? (
          <p className="text-sm text-gray-500">No education added</p>
        ) : (
          <div className="space-y-2">
            {data.education.map((edu: Education, i: number) => (
              <div key={i} className="text-sm">
                <span className="font-medium text-gray-900">
                  {edu.degree}
                </span>
                {" — "}
                <span className="text-gray-700">{edu.institution}</span>
                {edu.field_of_study && (
                  <span className="text-gray-500">
                    {" "}
                    ({edu.field_of_study})
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Experience" onEdit={() => onEditStep(4)} step={4}>
        {data.experience.length === 0 ? (
          <p className="text-sm text-gray-500">No experience added</p>
        ) : (
          <div className="space-y-3">
            {data.experience.map((exp: Experience, i: number) => (
              <div key={i} className="text-sm">
                <div>
                  <span className="font-medium text-gray-900">{exp.title}</span>
                  {" at "}
                  <span className="text-gray-700">{exp.company}</span>
                  {exp.is_current && (
                    <span className="ml-2 text-xs text-green-600">
                      (Current)
                    </span>
                  )}
                </div>
                {exp.description && (
                  <p className="mt-1 text-gray-500">{exp.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="border-t border-gray-200 pt-4">
        <button
          type="button"
          onClick={onSubmit}
          disabled={loading}
          className="w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Saving your profile..." : "Complete Onboarding"}
        </button>
      </div>
    </div>
  );
}
