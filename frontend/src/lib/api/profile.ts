import { api } from "@/lib/api";
import type {
  Certification,
  CertificationCreate,
  CertificationUpdate,
  Education,
  EducationCreate,
  EducationUpdate,
  Experience,
  ExperienceCreate,
  ExperienceUpdate,
  Language,
  LanguageCreate,
  LanguageUpdate,
  ProfileDetail,
  ProfileMeResponse,
  ProfileUpdateRequest,
  Project,
  ProjectCreate,
  ProjectUpdate,
  Skill,
  SkillCreate,
  SkillUpdate,
  TargetRole,
  TargetRoleCreate,
  TargetRoleUpdate,
} from "@/types/profile";

export async function getProfileMe(): Promise<ProfileMeResponse> {
  return api.get<ProfileMeResponse>("/api/profile/me");
}

export async function getProfileFull(): Promise<ProfileDetail> {
  return api.get<ProfileDetail>("/api/profile/full");
}

export async function updateProfile(
  data: ProfileUpdateRequest,
): Promise<ProfileMeResponse> {
  return api.patch<ProfileMeResponse>("/api/profile/me", data);
}

// Education CRUD
export async function createEducation(
  data: EducationCreate,
): Promise<Education> {
  return api.post<Education>("/api/profile/educations", data);
}

export async function updateEducation(
  id: string,
  data: EducationUpdate,
): Promise<Education> {
  return api.put<Education>(`/api/profile/educations/${id}`, data);
}

export async function deleteEducation(id: string): Promise<void> {
  await api.delete(`/api/profile/educations/${id}`);
}

// Experience CRUD
export async function createExperience(
  data: ExperienceCreate,
): Promise<Experience> {
  return api.post<Experience>("/api/profile/experiences", data);
}

export async function updateExperience(
  id: string,
  data: ExperienceUpdate,
): Promise<Experience> {
  return api.put<Experience>(`/api/profile/experiences/${id}`, data);
}

export async function deleteExperience(id: string): Promise<void> {
  await api.delete(`/api/profile/experiences/${id}`);
}

// Skill CRUD
export async function createSkill(data: SkillCreate): Promise<Skill> {
  return api.post<Skill>("/api/profile/skills", data);
}

export async function updateSkill(
  id: string,
  data: SkillUpdate,
): Promise<Skill> {
  return api.put<Skill>(`/api/profile/skills/${id}`, data);
}

export async function deleteSkill(id: string): Promise<void> {
  await api.delete(`/api/profile/skills/${id}`);
}

// Project CRUD
export async function createProject(data: ProjectCreate): Promise<Project> {
  return api.post<Project>("/api/profile/projects", data);
}

export async function updateProject(
  id: string,
  data: ProjectUpdate,
): Promise<Project> {
  return api.put<Project>(`/api/profile/projects/${id}`, data);
}

export async function deleteProject(id: string): Promise<void> {
  await api.delete(`/api/profile/projects/${id}`);
}

// Target Role CRUD
export async function createTargetRole(
  data: TargetRoleCreate,
): Promise<TargetRole> {
  return api.post<TargetRole>("/api/profile/target-roles", data);
}

export async function updateTargetRole(
  id: string,
  data: TargetRoleUpdate,
): Promise<TargetRole> {
  return api.put<TargetRole>(`/api/profile/target-roles/${id}`, data);
}

export async function deleteTargetRole(id: string): Promise<void> {
  await api.delete(`/api/profile/target-roles/${id}`);
}

// Certification CRUD
export async function createCertification(
  data: CertificationCreate,
): Promise<Certification> {
  return api.post<Certification>("/api/profile/certifications", data);
}

export async function updateCertification(
  id: string,
  data: CertificationUpdate,
): Promise<Certification> {
  return api.put<Certification>(`/api/profile/certifications/${id}`, data);
}

export async function deleteCertification(id: string): Promise<void> {
  await api.delete(`/api/profile/certifications/${id}`);
}

// Language CRUD
export async function createLanguage(
  data: LanguageCreate,
): Promise<Language> {
  return api.post<Language>("/api/profile/languages", data);
}

export async function updateLanguage(
  id: string,
  data: LanguageUpdate,
): Promise<Language> {
  return api.put<Language>(`/api/profile/languages/${id}`, data);
}

export async function deleteLanguage(id: string): Promise<void> {
  await api.delete(`/api/profile/languages/${id}`);
}
