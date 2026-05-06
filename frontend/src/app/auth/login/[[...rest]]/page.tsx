"use client";

import { SignIn } from "@clerk/nextjs";
import { Suspense } from "react";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <a href="/" className="text-2xl font-bold text-gray-900">
            JobedIn
          </a>
        </div>
        <Suspense>
          <SignIn
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "rounded-lg shadow-sm ring-1 ring-gray-900/5",
              },
            }}
            signUpUrl="/auth/register"
          />
        </Suspense>
      </div>
    </div>
  );
}
