import { redirect } from "next/navigation";

export default async function LegacyPipelineJobPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  redirect(`/admin/jobs/${jobId}`);
}
