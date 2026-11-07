import { redirect } from "next/navigation";

export default function LegacyScansPage() {
  redirect("/dashboard/history");
}
