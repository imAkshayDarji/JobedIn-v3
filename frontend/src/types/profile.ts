export interface ProfileMeResponse {
  id: string;
  first_name: string;
  last_name: string;
  onboarding_completed: boolean;
  experience_level: string | null;
}

export interface ProfileUpdateRequest {
  first_name?: string | null;
  last_name?: string | null;
  headline?: string | null;
  summary?: string | null;
  location?: string | null;
  phone?: string | null;
  experience_level?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  website_url?: string | null;
}

export interface Education {
  id: string;
  created_at: string;
  updated_at: string;
  institution: string;
  degree: string;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  grade: string | null;
  description: string | null;
}

export interface EducationCreate {
  institution: string;
  degree: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  grade?: string;
  description?: string;
}

export interface EducationUpdate {
  institution?: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  grade?: string;
  description?: string;
}

export interface Experience {
  id: string;
  created_at: string;
  updated_at: string;
  company: string;
  title: string;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  is_current: boolean;
}

export interface ExperienceCreate {
  company: string;
  title: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  is_current?: boolean;
}

export interface ExperienceUpdate {
  company?: string;
  title?: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  is_current?: boolean;
}

export interface Skill {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  category: string | null;
  proficiency: string | null;
}

export interface SkillCreate {
  name: string;
  category?: string;
  proficiency?: string;
}

export interface SkillUpdate {
  name?: string;
  category?: string;
  proficiency?: string;
}

export interface Project {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  description: string | null;
  url: string | null;
  start_date: string | null;
  end_date: string | null;
  technologies: string | null;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  url?: string;
  start_date?: string;
  end_date?: string;
  technologies?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  url?: string;
  start_date?: string;
  end_date?: string;
  technologies?: string;
}

export interface TargetRole {
  id: string;
  created_at: string;
  updated_at: string;
  title: string;
  priority: number;
  keywords: string | null;
}

export interface TargetRoleCreate {
  title: string;
  priority?: number;
  keywords?: string;
}

export interface TargetRoleUpdate {
  title?: string;
  priority?: number;
  keywords?: string;
}

export interface Certification {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  issuer: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  credential_url: string | null;
}

export interface CertificationCreate {
  name: string;
  issuer?: string;
  issue_date?: string;
  expiry_date?: string;
  credential_url?: string;
}

export interface CertificationUpdate {
  name?: string;
  issuer?: string;
  issue_date?: string;
  expiry_date?: string;
  credential_url?: string;
}

export interface Language {
  id: string;
  created_at: string;
  updated_at: string;
  name: string;
  proficiency: string | null;
}

export interface LanguageCreate {
  name: string;
  proficiency?: string;
}

export interface LanguageUpdate {
  name?: string;
  proficiency?: string;
}

export interface ProfileDetail {
  id: string;
  created_at: string;
  updated_at: string;
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
  onboarding_completed: boolean;
  education: Education[];
  experience: Experience[];
  skills: Skill[];
  projects: Project[];
  target_roles: TargetRole[];
  certifications: Certification[];
  languages: Language[];
}
