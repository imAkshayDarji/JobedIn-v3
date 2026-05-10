import { auth } from "@clerk/nextjs/server";
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "JobedIn - AI-Powered Job Search",
  description:
    "Find your next role with AI-powered matching, resume optimization, and smart career insights.",
};

export default async function HomePage() {
  const { userId } = await auth();
  if (userId) {
    redirect("/dashboard");
  }

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <span className="text-xl font-bold text-gray-900">JobedIn</span>
        <nav className="flex gap-4">
          <Link
            href="/auth/login"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Sign In
          </Link>
          <Link
            href="/auth/register"
            className="text-sm font-medium text-white bg-blue-600 px-4 py-1.5 rounded-md hover:bg-blue-700"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 sm:text-6xl">
          Your next role,{" "}
          <span className="text-blue-600">powered by AI</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-gray-600">
          JobedIn uses intelligent matching, resume optimization, and career
          insights to connect you with opportunities that actually fit.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/auth/register"
            className="rounded-md bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Get Started
          </Link>
          <Link
            href="/auth/login"
            className="rounded-md border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Sign In
          </Link>
        </div>
      </main>

      <footer className="border-t border-gray-200 px-6 py-4 text-center text-sm text-gray-500">
        &copy; {new Date().getFullYear()} JobedIn. All rights reserved.
      </footer>
    </div>
  );
}
