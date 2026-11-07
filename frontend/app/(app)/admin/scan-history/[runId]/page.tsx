import { redirect } from "next/navigation";

export default async function AdminScanDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  redirect(`/dashboard/history/${runId}`);
}
