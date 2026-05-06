import "@testing-library/jest-dom/vitest";

// Mock Next.js navigation hooks
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
  redirect: vi.fn(),
  notFound: vi.fn(),
}));

// Mock next/link
vi.mock("next/link", () => {
  return {
    default: ({
      children,
      ...props
    }: {
      children: React.ReactNode;
      href: string;
    }) => {
      return <a {...props}>{children}</a>;
    },
  };
});

// Mock @sentry/nextjs
vi.mock("@sentry/nextjs", () => ({
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
  setContext: vi.fn(),
}));

// Mock sonner
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock @clerk/nextjs
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    isLoaded: true,
    isSignedIn: true,
    userId: "user_test_123",
    user: {
      primaryEmailAddress: { emailAddress: "test@example.com" },
      firstName: "Test",
      lastName: "User",
    },
  }),
  useClerk: () => ({
    signOut: vi.fn(),
  }),
  ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SignIn: () => <div data-testid="clerk-sign-in">SignIn</div>,
  SignUp: () => <div data-testid="clerk-sign-up">SignUp</div>,
}));

// Mock @clerk/nextjs/server
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({
    getToken: vi.fn().mockResolvedValue("test-token"),
    userId: "user_test_123",
  }),
}));
