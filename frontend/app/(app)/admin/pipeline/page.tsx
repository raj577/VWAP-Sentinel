import { redirect } from "next/navigation";

export default function LegacyPipelinePage() {
  redirect("/admin/scheduler");
}
