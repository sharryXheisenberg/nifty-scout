import { notFound } from "next/navigation";
import StatBar from "@/components/StatBar";
import PlayerCard from "@/components/PlayerCard";
import { findPlayerBySymbol } from "@/lib/data";

export const revalidate = 3600;

export default async function StockDetailPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol } = await params;
  const result = await findPlayerBySymbol(symbol);
  if (!result) notFound();

  const { player, date } = result;

  return (
    <div>
      <div className="text-xs tracking-widest text-gold/80 font-mono mb-2">
        LAST SCOUTED — {date}
      </div>
      <h1 className="font-display text-3xl font-semibold mb-1">
        {player.name}
      </h1>
      <p className="text-ink-secondary mb-8">
        {player.symbol} &middot; {player.sector}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-10">
        <div>
          <PlayerCard player={player} linked={false} />
        </div>

        <div>
          <h2 className="font-display text-lg mb-4 text-ink-secondary">
            Scout breakdown
          </h2>
          <StatBar label="Momentum (EMA cross)" value={player.momentum} />
          <StatBar label="Volume surge" value={player.volume_surge} />
          <StatBar
            label="Volatility-adjusted return"
            value={player.volatility_adj_return}
          />
          <StatBar
            label="Drawdown penalty"
            value={-player.drawdown_penalty}
            min={-1}
            max={1}
          />

          <div className="mt-8 grid grid-cols-2 gap-4 text-sm">
            <div className="bg-navy-card/80 border border-white/10 rounded-lg p-4">
              <div className="text-ink-muted text-xs mb-1">Latest close</div>
              <div className="font-mono text-lg text-white">
                ₹{player.latest_close.toLocaleString("en-IN")}
              </div>
            </div>
            <div className="bg-navy-card/80 border border-white/10 rounded-lg p-4">
              <div className="text-ink-muted text-xs mb-1">Latest volume</div>
              <div className="font-mono text-lg text-white">
                {player.latest_volume.toLocaleString("en-IN")}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
