import Link from "next/link";
import type { PlayerCard as PlayerCardType } from "@/lib/types";

const POSITION_LABELS: Record<string, string> = {
  FWD: "Forward",
  MID: "Midfield",
  DEF: "Defender",
};

interface PlayerCardProps {
  player: PlayerCardType;
  /** Renders a smaller variant for dense grids (leaderboard, archive previews). */
  compact?: boolean;
  /** Wrap the card in a link to its stock detail page. Defaults to true. */
  linked?: boolean;
}

export default function PlayerCard({
  player,
  compact = false,
  linked = true,
}: PlayerCardProps) {
  const displaySymbol = player.symbol.replace(".NS", "");
  const scoreColor =
    player.composite_score >= 0 ? "text-gold" : "text-red-400";

  const content = (
    <div
      className={`bg-navy-card/90 border border-gold/60 rounded-xl text-center shadow-lg shadow-black/30 hover:border-gold transition-colors ${
        compact ? "p-3 w-[140px]" : "p-4 w-[200px]"
      }`}
    >
      <span className="inline-block text-[10px] font-semibold text-navy bg-gold px-2.5 py-0.5 rounded-full">
        {player.position}
      </span>
      <div
        className={`font-display font-semibold text-white mt-2 ${
          compact ? "text-sm" : "text-lg"
        }`}
      >
        {displaySymbol}
      </div>
      {!compact && (
        <div className="text-xs text-ink-secondary mt-0.5 truncate">
          {player.name}
        </div>
      )}
      <div className={`font-mono font-semibold mt-2 ${scoreColor} ${compact ? "text-base" : "text-2xl"}`}>
        {player.composite_score >= 0 ? "+" : ""}
        {player.composite_score.toFixed(2)}
      </div>
      {!compact && (
        <div className="flex justify-between text-[10px] text-ink-secondary mt-2 border-t border-white/10 pt-1.5 font-mono">
          <span>MOM {player.momentum >= 0 ? "+" : ""}{player.momentum.toFixed(2)}</span>
          <span>VOL {player.volume_surge >= 0 ? "+" : ""}{player.volume_surge.toFixed(2)}</span>
        </div>
      )}
    </div>
  );

  if (!linked) return content;

  return (
    <Link
      href={`/stock/${displaySymbol}`}
      aria-label={`View details for ${player.name}, ${POSITION_LABELS[player.position]}`}
    >
      {content}
    </Link>
  );
}
