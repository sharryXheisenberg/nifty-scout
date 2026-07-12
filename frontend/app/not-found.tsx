import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-center py-24">
      <div className="font-display text-6xl text-gold mb-4">Offside</div>
      <p className="text-ink-secondary mb-8">
        That page, stock, or matchday doesn&apos;t exist in the archive.
      </p>
      <Link
        href="/"
        className="inline-block px-5 py-2.5 rounded-lg bg-gold text-navy font-semibold text-sm hover:bg-gold/90 transition-colors"
      >
        Back to today&apos;s lineup
      </Link>
    </div>
  );
}
