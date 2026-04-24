import { z } from "zod";

export const personalInfoSchema = z.object({
  first_name: z.string().min(1, "First name is required").max(100),
  last_name: z.string().min(1, "Last name is required").max(100),
  headline: z.string().max(200).nullable().default(null),
  summary: z.string().max(5000).nullable().default(null),
  location: z.string().max(200).nullable().default(null),
  phone: z.string().max(50).nullable().default(null),
  experience_level: z.string().nullable().default(null),
  linkedin_url: z.string().max(500).nullable().default(null),
  github_url: z.string().max(500).nullable().default(null),
  portfolio_url: z.string().max(500).nullable().default(null),
  website_url: z.string().max(500).nullable().default(null),
});

export const targetRoleSchema = z.object({
  title: z.string().min(1, "Job title is required").max(200),
  priority: z.number().int().min(0).max(10).default(0),
  keywords: z.string().max(1000).nullable().default(null),
});

export const skillSchema = z.object({
  name: z.string().min(1, "Skill name is required").max(100),
  category: z.string().max(100).nullable().default(null),
  proficiency: z.string().max(50).nullable().default(null),
});

export const educationSchema = z.object({
  institution: z.string().min(1, "Institution is required").max(200),
  degree: z.string().min(1, "Degree is required").max(200),
  field_of_study: z.string().max(200).nullable().default(null),
  start_date: z.string().nullable().default(null),
  end_date: z.string().nullable().default(null),
  grade: z.string().max(50).nullable().default(null),
  description: z.string().max(2000).nullable().default(null),
});

export const experienceSchema = z.object({
  company: z.string().min(1, "Company is required").max(200),
  title: z.string().min(1, "Job title is required").max(200),
  location: z.string().max(200).nullable().default(null),
  start_date: z.string().nullable().default(null),
  end_date: z.string().nullable().default(null),
  description: z.string().max(2000).nullable().default(null),
  is_current: z.boolean().default(false),
});

export const onboardingSchema = z.object({
  personal_info: personalInfoSchema,
  target_roles: z.array(targetRoleSchema).default([]),
  skills: z.array(skillSchema).default([]),
  education: z.array(educationSchema).default([]),
  experience: z.array(experienceSchema).default([]),
});
