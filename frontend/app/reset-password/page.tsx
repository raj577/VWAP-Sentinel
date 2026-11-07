export const dynamic = "force-dynamic";

import Link from "next/link";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { ResetPasswordForm } from "@/components/ResetPasswordForm";

export const metadata = {
  title: "Reset password — AVWAP Scanner",
};

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;
  return (
    <AuthLayout
      title="Reset password"
      subtitle="Set a new password. Existing sessions will be revoked."
      footer={
        <span>
          Need to sign in instead?{" "}
          <Link href="/login" className="text-mint/90 hover:text-mint">
            Login
          </Link>
          .
        </span>
      }
    >
      <ResetPasswordForm initialToken={params.token ?? ""} />
    </AuthLayout>
  );
}
