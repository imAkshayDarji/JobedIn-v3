interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <a href="/" className="text-2xl font-bold text-gray-900">
            JobedIn
          </a>
        </div>

        <div className="rounded-lg bg-white px-8 py-10 shadow-sm ring-1 ring-gray-900/5">
          <h2 className="text-center text-xl font-semibold text-gray-900">
            {title}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}
