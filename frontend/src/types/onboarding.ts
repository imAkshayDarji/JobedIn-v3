export interface PersonalInfo {
  first_name: string;
  last_name: string;
  headline: string | null;
  summary: string | null;
  location: string | null;
  phone: string | null;
  experience_level: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  website_url: string | null;
}

export interface TargetRole {
  title: string;
  priority: number;
  keywords: string | null;
}

export interface Skill {
  name: string;
  category: string | null;
  proficiency: string | null;
}

export interface Education {
  institution: string;
  degree: string;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  grade: string | null;
  description: string | null;
}

export interface Experience {
  company: string;
  title: string;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  is_current: boolean;
}

export interface OnboardingSaveRequest {
  personal_info: PersonalInfo;
  target_roles: TargetRole[];
  skills: Skill[];
  education: Education[];
  experience: Experience[];
}

export interface OnboardingSaveResponse {
  profile_id: string;
  created_target_roles: number;
  created_skills: number;
  created_education: number;
  created_experience: number;
}

export interface OnboardingStatusResponse {
  onboarding_step: number;
  onboarding_completed: boolean;
  completion_percentage: number;
  completed_sections: string[];
  next_step: number;
  personal_info: PersonalInfo | null;
  target_roles: TargetRole[];
  skills: Skill[];
  education: Education[];
  experience: Experience[];
}

export interface ResumeUploadResponse {
  extracted_text: string;
  page_count: number;
  pre_fill: {
    personal_info: PersonalInfo | null;
    target_roles: TargetRole[];
    skills: Skill[];
    education: Education[];
    experience: Experience[];
  };
}
