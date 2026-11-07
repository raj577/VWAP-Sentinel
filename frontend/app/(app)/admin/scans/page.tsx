import { redirect } from "next/navigation";

export default function LegacyAdminScansPage() {
  redirect("/admin/scan-history");
}
