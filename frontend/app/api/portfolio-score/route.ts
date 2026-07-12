import { NextRequest, NextResponse } from "next/server";
import { fetchDailyBars } from "@/lib/yahoo";
import { computeRawFactors, scoreBatch } from "@/lib/scoring";
import type { PortfolioScoreResult, PlayerCard, Position } from "@/lib/types";

export const runtime = "nodejs";

const MAX_SYMBOLS_PER_REQUEST = 15;

function assignPositions(count: number): Position[] {
  // Simple tertile split so the portfolio result can still render on a
  // formation pitch: top third FWD, middle third MID, rest DEF.
  const positions: Position[] = [];
  const fwdCount = Math.ceil(count / 3);
  const midCount = Math.ceil((count - fwdCount) / 2);
  for (let i = 0; i < count; i++) {
    if (i < fwdCount) positions.push("FWD");
    else if (i < fwdCount + midCount) positions.push("MID");
    else positions.push("DEF");
  }
  return positions;
}

export async function POST(request: NextRequest) {
  let body: { symbols?: string[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Request body must be valid JSON with a `symbols` array." },
      { status: 400 }
    );
  }

  const rawSymbols = Array.isArray(body.symbols) ? body.symbols : [];
  const symbols = rawSymbols
    .map((s) => String(s).trim().toUpperCase())
    .filter((s) => s.length > 0)
    .slice(0, MAX_SYMBOLS_PER_REQUEST);

  if (symbols.length === 0) {
    return NextResponse.json(
      { error: "Provide at least one NSE ticker symbol, e.g. TCS or RELIANCE." },
      { status: 400 }
    );
  }

  const excluded: { symbol: string; reason: string }[] = [];
  const scored: {
    symbol: string;
    factors: ReturnType<typeof computeRawFactors>;
  }[] = [];

  const results = await Promise.all(
    symbols.map(async (symbol) => {
      const bars = await fetchDailyBars(symbol);
      if (!bars) {
        return { symbol, error: "No data found for this symbol" as string };
      }
      const factors = computeRawFactors(bars);
      if (!factors) {
        return { symbol, error: "Not enough trading history to score" as string };
      }
      return { symbol, factors };
    })
  );

  for (const r of results) {
    if ("error" in r && r.error) {
      excluded.push({ symbol: r.symbol, reason: r.error });
    } else if ("factors" in r && r.factors) {
      scored.push({ symbol: r.symbol, factors: r.factors });
    }
  }

  if (scored.length === 0) {
    const payload: PortfolioScoreResult = {
      date: new Date().toISOString().slice(0, 10),
      players: [],
      excluded,
    };
    return NextResponse.json(payload, { status: 200 });
  }

  const blended = scoreBatch(
    scored.map((s) => ({ symbol: s.symbol, factors: s.factors! }))
  ).sort((a, b) => b.composite - a.composite);

  const positions = assignPositions(blended.length);

  const players: PlayerCard[] = blended.map((entry, i) => ({
    symbol: entry.symbol.endsWith(".NS") ? entry.symbol : `${entry.symbol}.NS`,
    name: entry.symbol.replace(".NS", ""),
    sector: "—",
    position: positions[i],
    composite_score: Number(entry.composite.toFixed(4)),
    momentum: Number(entry.factors.momentum.toFixed(4)),
    volume_surge: Number(entry.factors.volumeSurge.toFixed(4)),
    volatility_adj_return: Number(entry.factors.volatilityAdjReturn.toFixed(4)),
    drawdown_penalty: Number(entry.factors.drawdownPenalty.toFixed(4)),
    latest_close: 0,
    latest_volume: 0,
  }));

  const payload: PortfolioScoreResult = {
    date: new Date().toISOString().slice(0, 10),
    players,
    excluded,
  };

  return NextResponse.json(payload, { status: 200 });
}
