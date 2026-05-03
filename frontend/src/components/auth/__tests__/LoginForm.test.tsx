import { beforeEach, describe, expect, it, vi } from "vitest";

import { createClient } from "@/lib/supabase/client";

import { render, screen, fireEvent } from "@/test/utils";

import { LoginForm } from "../LoginForm";

let mockSignIn: ReturnType<typeof vi.fn>;

vi.mock("@/lib/supabase/client", () => {
  const signIn = vi.fn();
  let _signIn = signIn;
  return {
    createClient: () => ({
      auth: {
        getSession: vi.fn().mockResolvedValue({
          data: { session: { access_token: "test-token" } },
        }),
        signInWithPassword: (...args: unknown[]) => _signIn(...args),
        signUp: vi.fn(),
        signOut: vi.fn(),
      },
    }),
    __setSignIn: (fn: ReturnType<typeof vi.fn>) => {
      _signIn = fn;
    },
  };
});

const mockedModule = vi.mocked(
  await import("@/lib/supabase/client"),
) as unknown as {
  __setSignIn: (fn: ReturnType<typeof vi.fn>) => void;
};

describe("LoginForm", () => {
  beforeEach(() => {
    mockSignIn = vi.fn();
    mockedModule.__setSignIn(mockSignIn);
  });

  it("renders email and password inputs", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders submit button", () => {
    render(<LoginForm />);
    expect(
      screen.getByRole("button", { name: "Sign In" }),
    ).toBeInTheDocument();
  });

  it("calls signInWithPassword on form submit with correct values", async () => {
    mockSignIn.mockResolvedValue({ error: null });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await vi.waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({
        email: "user@example.com",
        password: "secret123",
      });
    });
  });

  it("shows error message on failed login", async () => {
    mockSignIn.mockResolvedValue({
      error: { message: "Invalid login credentials" },
    });

    render(<LoginForm />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "bad@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await vi.waitFor(() => {
      expect(
        screen.getByText("Invalid login credentials"),
      ).toBeInTheDocument();
    });
  });
});
