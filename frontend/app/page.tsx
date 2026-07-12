import FormationPitch from "@/components/FormationPitch";
import ShareCardButton from "@/components/ShareCardButton";
import { getLatestReport } from "@/lib/data";

export const revalidate = 3600; // re-check for a new report hourly

export default async function HomePage() {
  const report = await getLatestReport();

  return (
    <div>
      <section className="mb-10">
        <div className="text-xs tracking-widest text-gold/80 font-mono mb-2">
          {report ? `MATCHDAY — ${report.date}` : "NO REPORT YET"}
        </div>
        <h1 className="font-display text-4xl sm:text-5xl font-semibold leading-tight">
          Today&apos;s Team of the Week
        </h1>
        <p className="text-ink-secondary mt-3 max-w-xl">
          The NSE&apos;s highest-scoring stocks today, scouted on momentum,
          volume surge, and risk-adjusted return — laid out like a matchday
          lineup.
        </p>
      </section>

      <FormationPitch
        players={report?.players ?? []}
        formation={report?.formation ?? "4-3-3"}
      />

      {report && report.players.length > 0 && (
        <div className="mt-6">
          <ShareCardButton
            shareText={`Nifty Scout Report — ${report.date}'s Team of the Week`}
          />
        </div>
      )}
    </div>
  );
}
