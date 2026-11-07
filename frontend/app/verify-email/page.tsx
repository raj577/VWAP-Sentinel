export const dynamic = "force-dynamic";

import Link from "next/link";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { VerifyEmailPanel } from "@/components/VerifyEmailPanel";

export const metadata = {
  title: "Verify email — AVWAP Scanner",
};

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;
  return (
    <AuthLayout
      title="Verify your email"
      subtitle="Confirm your address to activate the account."
      footer={
        <span>
          Already verified?{" "}
          <Link href="/login" className="text-mint/90 hover:text-mint">
            Sign in
          </Link>
          .
        </span>
      }
    >
      <VerifyEmailPanel initialToken={params.token ?? ""} />
    </AuthLayout>
  );
}
