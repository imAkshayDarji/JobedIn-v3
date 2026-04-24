import { AuthLayout } from "@/components/auth/AuthLayout";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { OAuthButtons } from "@/components/auth/OAuthButtons";

export const metadata = {
  title: "Create Account - JobedIn",
};

export default function RegisterPage() {
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Get started with JobedIn for free"
    >
      <div className="space-y-6">
        <OAuthButtons mode="register" />
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
        <RegisterForm />
      </div>
    </AuthLayout>
  );
}
