import Link from "next/link";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { ForgotPasswordForm } from "@/components/ForgotPasswordForm";

export const metadata = {
  title: "Forgot password — AVWAP Scanner",
};

export default function ForgotPasswordPage() {
  return (
    <AuthLayout
      title="Forgot password"
      subtitle="We will email a single-use reset link if the account exists."
      footer={
        <span>
          Remembered it?{" "}
          <Link href="/login" className="text-mint/90 hover:text-mint">
            Back to sign in
          </Link>
          .
        </span>
      }
    >
      <ForgotPasswordForm />
    </AuthLayout>
  );
}
