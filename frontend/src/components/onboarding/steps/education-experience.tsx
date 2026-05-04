"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import type { Education, Experience } from "@/types/onboarding";

interface EducationExperienceProps {
  education: Education[];
  experience: Experience[];
  onUpdate: (education: Education[], experience: Experience[]) => void;
}

export function EducationExperience({
  education,
  experience,
  onUpdate,
}: EducationExperienceProps) {
  const [edu, setEdu] = useState<Education[]>(education);
  const [exp, setExp] = useState<Experience[]>(experience);

  const addEducation = () => {
    const updated = [
      ...edu,
      {
        institution: "",
        degree: "",
        field_of_study: null,
        start_date: null,
        end_date: null,
        grade: null,
        description: null,
      },
    ];
    setEdu(updated);
    onUpdate(updated, exp);
  };

  const removeEducation = (index: number) => {
    const updated = edu.filter((_, i) => i !== index);
    setEdu(updated);
    onUpdate(updated, exp);
  };

  const updateEducation = (
    index: number,
    field: keyof Education,
    value: string,
  ) => {
    const updated = edu.map((e, i) =>
      i === index ? { ...e, [field]: value || null } : e,
    );
    setEdu(updated);
    onUpdate(updated, exp);
  };

  const addExperience = () => {
    const updated = [
      ...exp,
      {
        company: "",
        title: "",
        location: null,
        start_date: null,
        end_date: null,
        description: null,
        is_current: false,
      },
    ];
    setExp(updated);
    onUpdate(edu, updated);
  };

  const removeExperience = (index: number) => {
    const updated = exp.filter((_, i) => i !== index);
    setExp(updated);
    onUpdate(edu, updated);
  };

  const updateExperience = (
    index: number,
    field: keyof Experience,
    value: string | boolean,
  ) => {
    const updated = exp.map((e, i) =>
      i === index ? { ...e, [field]: value } : e,
    );
    setExp(updated);
    onUpdate(edu, updated);
  };

  return (
    <div className="space-y-8">
      {/* Education Section */}
      <div>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Education</h3>
          <button
            type="button"
            onClick={addEducation}
            className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            <Plus className="h-4 w-4" />
            Add Education
          </button>
        </div>

        <div className="mt-3 space-y-3">
          {edu.map((item, index) => (
            <div
              key={index}
              className="rounded-md border border-gray-200 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <input
                      type="text"
                      placeholder="Institution *"
                      value={item.institution}
                      onChange={(e) =>
                        updateEducation(index, "institution", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Degree *"
                      value={item.degree}
                      onChange={(e) =>
                        updateEducation(index, "degree", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                  <input
                    type="text"
                    placeholder="Field of Study"
                    value={item.field_of_study ?? ""}
                    onChange={(e) =>
                      updateEducation(index, "field_of_study", e.target.value)
                    }
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  />
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <input
                      type="date"
                      placeholder="Start Date"
                      value={item.start_date ?? ""}
                      onChange={(e) =>
                        updateEducation(index, "start_date", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                    <input
                      type="date"
                      placeholder="End Date"
                      value={item.end_date ?? ""}
                      onChange={(e) =>
                        updateEducation(index, "end_date", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Grade / GPA"
                      value={item.grade ?? ""}
                      onChange={(e) =>
                        updateEducation(index, "grade", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeEducation(index)}
                  className="ml-3 mt-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
          {edu.length === 0 && (
            <p className="py-4 text-center text-sm text-gray-500">
              No education added yet.
            </p>
          )}
        </div>
      </div>

      {/* Experience Section */}
      <div className="border-t border-gray-200 pt-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            Work Experience
          </h3>
          <button
            type="button"
            onClick={addExperience}
            className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            <Plus className="h-4 w-4" />
            Add Experience
          </button>
        </div>

        <div className="mt-3 space-y-3">
          {exp.map((item, index) => (
            <div
              key={index}
              className="rounded-md border border-gray-200 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <input
                      type="text"
                      placeholder="Company *"
                      value={item.company}
                      onChange={(e) =>
                        updateExperience(index, "company", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Job Title *"
                      value={item.title}
                      onChange={(e) =>
                        updateExperience(index, "title", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                  </div>
                  <input
                    type="text"
                    placeholder="Location"
                    value={item.location ?? ""}
                    onChange={(e) =>
                      updateExperience(index, "location", e.target.value)
                    }
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  />
                  <div className="flex items-center gap-3">
                    <input
                      type="date"
                      value={item.start_date ?? ""}
                      onChange={(e) =>
                        updateExperience(index, "start_date", e.target.value)
                      }
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                    />
                    <span className="text-sm text-gray-400">to</span>
                    <input
                      type="date"
                      value={item.end_date ?? ""}
                      onChange={(e) =>
                        updateExperience(index, "end_date", e.target.value)
                      }
                      disabled={item.is_current}
                      className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={item.is_current}
                      onChange={(e) =>
                        updateExperience(index, "is_current", e.target.checked)
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    Currently working here
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Description of your role..."
                    value={item.description ?? ""}
                    onChange={(e) =>
                      updateExperience(index, "description", e.target.value)
                    }
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeExperience(index)}
                  className="ml-3 mt-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
          {exp.length === 0 && (
            <p className="py-4 text-center text-sm text-gray-500">
              No work experience added yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
