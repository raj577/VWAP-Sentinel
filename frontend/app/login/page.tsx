import Link from "next/link";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata = {
  title: "Sign in — AVWAP Scanner",
  description: "Sign in to your AVWAP Scanner futures research dashboard.",
};

export default function LoginPage() {
  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to access your futures market intelligence."
      footer={
        <span>
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-mint/90 hover:text-mint">
            Create an account
          </Link>
          .
        </span>
      }
    >
      <LoginForm />
    </AuthLayout>
  );
}
