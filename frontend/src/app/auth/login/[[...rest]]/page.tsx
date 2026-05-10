"use client";

import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

const DEFAULT_AFTER_SIGN_IN = "/dashboard";
const DEFAULT_AFTER_SIGN_UP = "/onboarding";

function safeInternalPath(raw: string | null, fallback: string): string {
  if (raw == null || raw === "") return fallback;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw);
  } catch {
    return fallback;
  }
  if (!decoded.startsWith("/") || decoded.startsWith("//")) return fallback;
  return decoded;
}

function SignInWithRedirect() {
  const searchParams = useSearchParams();
  const afterSignIn = useMemo(
    () => safeInternalPath(searchParams.get("redirect"), DEFAULT_AFTER_SIGN_IN),
    [searchParams],
  );

  return (
    <SignIn
      appearance={{
        elements: {
          rootBox: "w-full",
          card: "rounded-lg shadow-sm ring-1 ring-gray-900/5",
        },
      }}
      fallbackRedirectUrl={afterSignIn}
      signUpFallbackRedirectUrl={DEFAULT_AFTER_SIGN_UP}
      signUpUrl="/auth/register"
    />
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Link href="/" className="text-2xl font-bold text-gray-900">
            JobedIn
          </Link>
        </div>
        <Suspense>
          <SignInWithRedirect />
        </Suspense>
      </div>
    </div>
  );
}
