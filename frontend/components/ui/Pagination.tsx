import Link from "next/link";

export function Pagination({
  page,
  totalPages,
  buildHref,
}: {
  page: number;
  totalPages: number;
  buildHref: (page: number) => string;
}) {
  if (totalPages <= 1) {
    return <p className="text-xs text-mist">Page 1 of 1</p>;
  }
  return (
    <div className="flex items-center gap-3 text-xs text-mist">
      <span>
        Page {page} of {totalPages}
      </span>
      {page > 1 ? (
        <Link href={buildHref(page - 1)} className="rounded border border-white/10 px-2 py-1 hover:text-white">
          Previous
        </Link>
      ) : (
        <span className="rounded border border-white/[0.06] px-2 py-1 opacity-40">
          Previous
        </span>
      )}
      {page < totalPages ? (
        <Link href={buildHref(page + 1)} className="rounded border border-white/10 px-2 py-1 hover:text-white">
          Next
        </Link>
      ) : (
        <span className="rounded border border-white/[0.06] px-2 py-1 opacity-40">
          Next
        </span>
      )}
    </div>
  );
}
