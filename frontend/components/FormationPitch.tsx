import PlayerCard from "./PlayerCard";
import type { PlayerCard as PlayerCardType } from "@/lib/types";

interface FormationPitchProps {
  players: PlayerCardType[];
  formation?: string;
}

/** Groups players by position, preserving composite-score order within each row. */
function groupByPosition(players: PlayerCardType[]) {
  return {
    FWD: players.filter((p) => p.position === "FWD"),
    MID: players.filter((p) => p.position === "MID"),
    DEF: players.filter((p) => p.position === "DEF"),
  };
}

export default function FormationPitch({
  players,
  formation = "4-3-3",
}: FormationPitchProps) {
  const { FWD, MID, DEF } = groupByPosition(players);

  if (players.length === 0) {
    return (
      <div className="bg-pitch-gradient rounded-2xl border-2 border-white/15 p-16 text-center">
        <p className="text-ink-secondary">
          No lineup available yet. Run the backend pipeline to generate today&apos;s report.
        </p>
      </div>
    );
  }

  return (
    <div
      id="formation-pitch"
      className="relative bg-pitch-gradient rounded-2xl border-2 border-white/15 px-4 py-10 sm:px-10"
    >
      <div className="absolute left-6 right-6 top-1/2 h-px bg-white/20" aria-hidden />
      <div className="text-center text-xs text-white/40 tracking-widest mb-8 font-mono">
        FORMATION {formation}
      </div>

      <div className="flex flex-wrap justify-center gap-4 mb-16">
        {FWD.map((p) => (
          <PlayerCard key={p.symbol} player={p} />
        ))}
      </div>
      <div className="flex flex-wrap justify-center gap-4 mb-16">
        {MID.map((p) => (
          <PlayerCard key={p.symbol} player={p} />
        ))}
      </div>
      <div className="flex flex-wrap justify-center gap-4">
        {DEF.map((p) => (
          <PlayerCard key={p.symbol} player={p} compact />
        ))}
      </div>
    </div>
  );
}
