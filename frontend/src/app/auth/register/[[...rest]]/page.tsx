import { SignUp } from "@clerk/nextjs";
import Link from "next/link";

export const metadata = {
  title: "Create Account - JobedIn",
};

export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <Link href="/" className="text-2xl font-bold text-gray-900">
            JobedIn
          </Link>
        </div>
        <SignUp
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "rounded-lg shadow-sm ring-1 ring-gray-900/5",
            },
          }}
          fallbackRedirectUrl="/onboarding"
          signInFallbackRedirectUrl="/dashboard"
          signInUrl="/auth/login"
        />
      </div>
    </div>
  );
}
