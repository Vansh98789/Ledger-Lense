import Link from "next/link";
import { ScanSearch } from "lucide-react";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2.5 group">
      <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-shadow">
        <ScanSearch className="w-4 h-4 text-white" />
      </span>
      <span className="text-base font-semibold tracking-tight text-slate-100">
        Ledger<span className="text-indigo-400">Lens</span>
      </span>
    </Link>
  );
}
