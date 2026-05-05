"use client";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const AUTH_ERROR_MESSAGES: Record<string, string> = {
  auth_callback_failed:
    "Google sign-in failed. Please try again or use email/password.",
  auth_code_hash_mismatch:
    "Authentication failed due to a security mismatch. Please try again.",
};

function LoginContent() {
  const searchParams = useSearchParams();
  const errorCode = searchParams.get("error");
  const errorMessage = errorCode
    ? AUTH_ERROR_MESSAGES[errorCode] ?? "Authentication failed. Please try again."
    : null;

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your JobedIn account">
      <div className="space-y-6">
        {errorMessage && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {errorMessage}
          </div>
        )}
        <OAuthButtons mode="login" />
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white px-2 text-gray-500">
              or continue with email
            </span>
          </div>
        </div>
        <LoginForm />
      </div>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}
