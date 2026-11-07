import Link from "next/link";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { RegisterForm } from "@/components/RegisterForm";

export const metadata = {
  title: "Create account — AVWAP Scanner",
  description: "Create your AVWAP Scanner account.",
};

export default function RegisterPage() {
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Register with your email. No FYERS credentials are required."
      footer={
        <span>
          Already registered?{" "}
          <Link href="/login" className="text-mint/90 hover:text-mint">
            Sign in
          </Link>
          .
        </span>
      }
    >
      <RegisterForm />
    </AuthLayout>
  );
}
