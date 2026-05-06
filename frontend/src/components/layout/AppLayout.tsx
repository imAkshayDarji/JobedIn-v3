"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth, useClerk, useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";

interface AppLayoutProps {
  children: React.ReactNode;
}

interface UserInfo {
  email: string;
  first_name?: string;
  last_name?: string;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const pathname = usePathname();
  const { isLoaded } = useAuth();
  const { user } = useUser();
  const { signOut } = useClerk();

  const userInfo: UserInfo | null = user
    ? {
        email: user.primaryEmailAddress?.emailAddress ?? "",
        first_name: user.firstName ?? undefined,
        last_name: user.lastName ?? undefined,
      }
    : null;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleSignOut() {
    await signOut(() => router.push("/auth/login"));
  }

  const navLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/jobs", label: "Jobs" },
    { href: "/applications", label: "Applications" },
    { href: "/resumes", label: "Resumes" },
    { href: "/cover-letters", label: "Cover Letters" },
    { href: "/interview", label: "Interview Coach" },
  ];

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  function getUserInitials(): string {
    if (userInfo?.first_name && userInfo?.last_name) {
      return (userInfo.first_name[0] + userInfo.last_name[0]).toUpperCase();
    }
    if (userInfo?.email) {
      return userInfo.email[0].toUpperCase();
    }
    return "?";
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-xl font-bold text-gray-900">
              JobedIn
            </Link>
            <nav className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(link.href)
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div ref={dropdownRef} className="relative">
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                title={userInfo?.email}
              >
                {getUserInitials()}
              </button>

              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-gray-200 bg-white py-1 shadow-lg z-50">
                  <Link
                    href="/profile"
                    onClick={() => setDropdownOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Profile
                  </Link>
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      handleSignOut();
                    }}
                    className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden rounded-md p-2 text-gray-600 hover:bg-gray-50"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="border-t border-gray-200 md:hidden">
            <nav className="flex flex-col px-4 py-2">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    isActive(link.href)
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href="/profile"
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  isActive("/profile")
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                Profile
              </Link>
            </nav>
          </div>
        )}
      </header>

      <main>{children}</main>
    </div>
  );
}
