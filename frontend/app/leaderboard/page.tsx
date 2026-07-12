import Link from "next/link";
import { getLeaderboard } from "@/lib/data";

export const revalidate = 3600;

export default async function LeaderboardPage() {
  const leaders = await getLeaderboard(30);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold mb-2">
        Leaderboard
      </h1>
      <p className="text-ink-secondary mb-8">
        Average scout score across all appearances in the last 30 matchdays.
        Ranks consistency, not a single lucky day.
      </p>

      {leaders.length === 0 ? (
        <p className="text-ink-secondary">
          No leaderboard data yet — needs at least a few days of archived
          reports.
        </p>
      ) : (
        <div className="border border-white/10 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-navy-panel text-ink-secondary text-left">
              <tr>
                <th className="px-4 py-3 font-medium">#</th>
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium text-right">
                  Appearances
                </th>
                <th className="px-4 py-3 font-medium text-right">
                  Avg score
                </th>
              </tr>
            </thead>
            <tbody>
              {leaders.slice(0, 25).map((entry, i) => (
                <tr
                  key={entry.symbol}
                  className="border-t border-white/5 hover:bg-white/5"
                >
                  <td className="px-4 py-3 text-ink-muted font-mono">
                    {i + 1}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/stock/${entry.symbol.replace(".NS", "")}`}
                      className="font-display text-gold hover:underline"
                    >
                      {entry.symbol.replace(".NS", "")}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-ink-secondary">
                    {entry.name}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {entry.appearances}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gold">
                    {entry.avgScore >= 0 ? "+" : ""}
                    {entry.avgScore.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
