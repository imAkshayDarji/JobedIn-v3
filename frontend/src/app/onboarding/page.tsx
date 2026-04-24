"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { WizardLayout } from "@/components/onboarding/wizard-layout";
import { ResumeUpload } from "@/components/onboarding/steps/resume-upload";
import { PersonalDetails } from "@/components/onboarding/steps/personal-details";
import { SkillsForm } from "@/components/onboarding/steps/skills-form";
import { EducationExperience } from "@/components/onboarding/steps/education-experience";
import { ReviewConfirm } from "@/components/onboarding/steps/review-confirm";
import { getOnboardingStatus, saveOnboarding } from "@/lib/api/onboarding";
import type {
  OnboardingSaveRequest,
  OnboardingStatusResponse,
  ResumeUploadResponse,
} from "@/types/onboarding";

const STEP_LABELS = [
  "Resume",
  "Details",
  "Skills",
  "Background",
  "Review",
];
const TOTAL_STEPS = 5;

const DEFAULT_PERSONAL_INFO = {
  first_name: "",
  last_name: "",
  headline: null,
  summary: null,
  location: null,
  phone: null,
  experience_level: null,
  linkedin_url: null,
  github_url: null,
  portfolio_url: null,
  website_url: null,
};

const EMPTY_DATA: OnboardingSaveRequest = {
  personal_info: DEFAULT_PERSONAL_INFO,
  target_roles: [],
  skills: [],
  education: [],
  experience: [],
};

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<OnboardingSaveRequest>(EMPTY_DATA);

  useEffect(() => {
    async function loadStatus() {
      try {
        const status: OnboardingStatusResponse =
          await getOnboardingStatus();
        if (status.onboarding_completed) {
          router.replace("/dashboard");
          return;
        }
        const existingData: OnboardingSaveRequest = {
          personal_info: status.personal_info ?? DEFAULT_PERSONAL_INFO,
          target_roles: status.target_roles,
          skills: status.skills,
          education: status.education,
          experience: status.experience,
        };
        setFormData(existingData);
        if (status.onboarding_step > 0) {
          setCurrentStep(status.onboarding_step);
        }
      } catch {
        // Profile might not exist yet - user can proceed with empty form
      } finally {
        setPageLoading(false);
      }
    }
    loadStatus();
  }, [router]);

  const handleResumeUploaded = useCallback(
    (response: ResumeUploadResponse) => {
      if (response.pre_fill.personal_info) {
        setFormData((prev) => ({
          ...prev,
          personal_info: {
            ...DEFAULT_PERSONAL_INFO,
            ...response.pre_fill.personal_info,
          },
        }));
      }
      setCurrentStep(2);
    },
    [],
  );

  const handleSkipResume = useCallback(() => {
    setCurrentStep(2);
  }, []);

  const handlePersonalUpdate = useCallback(
    (info: typeof formData.personal_info, roles: typeof formData.target_roles) => {
      setFormData((prev) => ({ ...prev, personal_info: info, target_roles: roles }));
    },
    [],
  );

  const handleSkillsUpdate = useCallback(
    (skills: typeof formData.skills) => {
      setFormData((prev) => ({ ...prev, skills }));
    },
    [],
  );

  const handleEduExpUpdate = useCallback(
    (
      education: typeof formData.education,
      experience: typeof formData.experience,
    ) => {
      setFormData((prev) => ({ ...prev, education, experience }));
    },
    [],
  );

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      await saveOnboarding(formData);
      router.push("/dashboard");
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail ?? "Failed to save onboarding data");
    } finally {
      setLoading(false);
    }
  };

  const validateStep = (step: number): boolean => {
    if (step === 2) {
      return (
        formData.personal_info.first_name.trim() !== "" &&
        formData.personal_info.last_name.trim() !== ""
      );
    }
    return true;
  };

  if (pageLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          <p className="mt-3 text-sm text-gray-600">Loading your profile...</p>
        </div>
      </div>
    );
  }

  const stepMeta: Record<number, { title: string; subtitle: string }> = {
    1: {
      title: "Upload Your Resume",
      subtitle: "Upload a PDF resume to auto-fill your profile, or skip to enter details manually.",
    },
    2: {
      title: "Personal Details & Target Roles",
      subtitle: "Tell us about yourself and the roles you're targeting.",
    },
    3: {
      title: "Skills",
      subtitle: "Add your key professional skills.",
    },
    4: {
      title: "Education & Experience",
      subtitle: "Add your educational background and work history.",
    },
    5: {
      title: "Review & Confirm",
      subtitle: "Review everything before submitting.",
    },
  };

  const meta = stepMeta[currentStep];

  return (
    <WizardLayout
      currentStep={currentStep}
      totalSteps={TOTAL_STEPS}
      stepLabels={STEP_LABELS}
      title={meta.title}
      subtitle={meta.subtitle}
      onBack={() => setCurrentStep((s) => Math.max(1, s - 1))}
      onNext={
        currentStep < 5
          ? () => setCurrentStep((s) => s + 1)
          : undefined
      }
      nextDisabled={!validateStep(currentStep)}
      nextLabel={currentStep === 4 ? "Review" : "Continue"}
      loading={loading}
    >
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {currentStep === 1 && (
        <ResumeUpload
          onResumeUploaded={handleResumeUploaded}
          onSkip={handleSkipResume}
        />
      )}

      {currentStep === 2 && (
        <PersonalDetails
          personalInfo={formData.personal_info}
          targetRoles={formData.target_roles}
          onUpdate={handlePersonalUpdate}
        />
      )}

      {currentStep === 3 && (
        <SkillsForm
          skills={formData.skills}
          onUpdate={handleSkillsUpdate}
        />
      )}

      {currentStep === 4 && (
        <EducationExperience
          education={formData.education}
          experience={formData.experience}
          onUpdate={handleEduExpUpdate}
        />
      )}

      {currentStep === 5 && (
        <ReviewConfirm
          data={formData}
          onEditStep={setCurrentStep}
          onSubmit={handleSubmit}
          loading={loading}
        />
      )}
    </WizardLayout>
  );
}
