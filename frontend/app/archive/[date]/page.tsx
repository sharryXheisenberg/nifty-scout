import Link from "next/link";
import { getArchiveEntries } from "@/lib/data";

export const revalidate = 3600;

export default async function ArchivePage() {
  const entries = await getArchiveEntries(90);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold mb-2">Archive</h1>
      <p className="text-ink-secondary mb-8">
        Every past matchday, with the day&apos;s top scorer.
      </p>

      {entries.length === 0 ? (
        <p className="text-ink-secondary">
          No archived reports yet — they&apos;ll appear here once the daily
          pipeline has run a few times.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {entries.map((entry) => (
            <Link
              key={entry.date}
              href={`/archive/${entry.date}`}
              className="block bg-navy-card/80 border border-white/10 rounded-xl p-5 hover:border-gold/60 transition-colors"
            >
              <div className="text-xs font-mono text-ink-muted mb-2">
                {entry.date}
              </div>
              <div className="text-sm text-ink-secondary mb-1">Top scorer</div>
              <div className="font-display text-lg text-white">
                {entry.topScorer.symbol.replace(".NS", "")}
              </div>
              <div className="font-mono text-gold text-sm mt-1">
                +{entry.topScorer.composite_score.toFixed(2)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
