import { redirect } from "next/navigation";

export default function LegacyCurrentPage() {
  redirect("/dashboard/scanner");
}
