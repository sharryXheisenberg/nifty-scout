"use client";

import { useState } from "react";
import FormationPitch from "@/components/FormationPitch";
import ShareCardButton from "@/components/ShareCardButton";
import type { PortfolioScoreResult } from "@/lib/types";

export default function PortfolioPage() {
  const [input, setInput] = useState("TCS, INFY, RELIANCE, HDFCBANK, TITAN");
  const [result, setResult] = useState<PortfolioScoreResult | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const symbols = input
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (symbols.length === 0) {
      setStatus("error");
      setErrorMessage("Enter at least one NSE ticker symbol.");
      return;
    }

    setStatus("loading");
    setErrorMessage("");
    try {
      const res = await fetch("/api/portfolio-score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbols }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus("error");
        setErrorMessage(data.error ?? "Something went wrong scoring your tickers.");
        return;
      }
      setResult(data);
      setStatus("idle");
    } catch {
      setStatus("error");
      setErrorMessage("Couldn't reach the scoring service. Try again in a moment.");
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold mb-2">Your XI</h1>
      <p className="text-ink-secondary mb-8 max-w-xl">
        Paste any NSE tickers, comma-separated, and get them scored and
        laid out the same way as the daily Team of the Week.
      </p>

      <form onSubmit={handleSubmit} className="mb-10">
        <label htmlFor="tickers" className="block text-sm text-ink-secondary mb-2">
          NSE tickers (comma-separated, up to 15)
        </label>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            id="tickers"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="TCS, INFY, RELIANCE"
            className="flex-1 bg-navy-card border border-white/15 rounded-lg px-4 py-2.5 text-sm focus:border-gold outline-none"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="px-5 py-2.5 rounded-lg bg-gold text-navy font-semibold text-sm hover:bg-gold/90 transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {status === "loading" ? "Scoring..." : "Score my XI"}
          </button>
        </div>
        {status === "error" && (
          <p className="text-sm text-red-400 mt-2">{errorMessage}</p>
        )}
      </form>

      {result && (
        <>
          {result.excluded.length > 0 && (
            <div className="mb-6 text-sm text-ink-muted">
              Skipped: {result.excluded.map((e) => `${e.symbol} (${e.reason})`).join(", ")}
            </div>
          )}

          <FormationPitch players={result.players} formation="Custom" />

          {result.players.length > 0 && (
            <div className="mt-6">
              <ShareCardButton
                filename="my-nifty-scout-xi.png"
                shareText="I just scored my own stock XI on Nifty Scout Report"
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
