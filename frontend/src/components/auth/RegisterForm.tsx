"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface RegisterFormProps {
  onSuccess?: () => void;
}

const ERROR_MESSAGES: Record<string, string> = {
  email_rate_limit_exceeded:
    "Too many attempts. Please wait a few minutes before trying again.",
  user_already_exists:
    "An account with this email already exists. Try signing in instead.",
  "already registered":
    "An account with this email already exists. Try signing in instead.",
  weak_password:
    "Password is too weak. Use at least 6 characters with a mix of letters and numbers.",
};

function getFriendlyError(message: string): string {
  for (const [code, friendly] of Object.entries(ERROR_MESSAGES)) {
    if (message.includes(code)) return friendly;
  }
  return message;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);
  const router = useRouter();

  async function handleResend() {
    setResending(true);
    setResent(false);
    const supabase = createClient();
    const { error: resendError } = await supabase.auth.resend({
      type: "signup",
      email,
    });
    setResending(false);
    if (resendError) {
      setError(getFriendlyError(resendError.message));
      return;
    }
    setResent(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    const supabase = createClient();

    const { data, error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (authError) {
      setLoading(false);
      setError(getFriendlyError(authError.message));
      return;
    }

    try {
      await api.post("/api/auth/sync-profile");
    } catch {
      // Non-blocking: backend _get_profile will auto-create if needed
    }

    setLoading(false);

    if (data.session) {
      if (onSuccess) {
        onSuccess();
        return;
      }
      router.push("/onboarding");
      return;
    }

    setConfirmationSent(true);
  }

  if (confirmationSent) {
    return (
      <div className="space-y-4 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <svg
            className="h-6 w-6 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">
          Check your email
        </h3>
        <p className="text-sm text-gray-600">
          We sent a confirmation link to{" "}
          <span className="font-medium text-gray-900">{email}</span>. Click the
          link to verify your account and get started.
        </p>
        <div className="space-y-2">
          <button
            type="button"
            onClick={handleResend}
            disabled={resending}
            className="text-sm font-medium text-blue-600 hover:text-blue-500 disabled:opacity-50"
          >
            {resending ? "Sending..." : "Resend confirmation email"}
          </button>
          {resent && (
            <p className="text-sm text-green-600">
              Confirmation email resent successfully.
            </p>
          )}
        </div>
        <p className="text-sm text-gray-500">
          Already confirmed?{" "}
          <Link
            href="/auth/login"
            className="font-medium text-blue-600 hover:text-blue-500"
          >
            Sign in
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div>
        <label
          htmlFor="register-email"
          className="block text-sm font-medium text-gray-700"
        >
          Email
        </label>
        <input
          id="register-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label
          htmlFor="register-password"
          className="block text-sm font-medium text-gray-700"
        >
          Password
        </label>
        <input
          id="register-password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          placeholder="••••••••"
        />
      </div>

      <div>
        <label
          htmlFor="register-confirm-password"
          className="block text-sm font-medium text-gray-700"
        >
          Confirm Password
        </label>
        <input
          id="register-confirm-password"
          type="password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          placeholder="••••••••"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Creating account..." : "Create Account"}
      </button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{" "}
        <Link
          href="/auth/login"
          className="font-medium text-blue-600 hover:text-blue-500"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
