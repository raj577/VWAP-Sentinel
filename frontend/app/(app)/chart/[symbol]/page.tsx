import { redirect } from "next/navigation";

export default async function LegacyChartPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  redirect(`/dashboard/chart/${symbol}`);
}
