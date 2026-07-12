"use client";

import { useState } from "react";
import { toPng } from "html-to-image";

interface ShareCardButtonProps {
  /** DOM id of the element to capture (defaults to the formation pitch). */
  targetId?: string;
  filename?: string;
  shareText?: string;
}

export default function ShareCardButton({
  targetId = "formation-pitch",
  filename = "nifty-scout-report.png",
  shareText = "Today's Nifty Scout Report — Team of the Week",
}: ShareCardButtonProps) {
  const [status, setStatus] = useState<"idle" | "working" | "error">("idle");

  async function captureImage(): Promise<string | null> {
    const node = document.getElementById(targetId);
    if (!node) {
      setStatus("error");
      return null;
    }
    try {
      setStatus("working");
      const dataUrl = await toPng(node, {
        backgroundColor: "#0b1220",
        pixelRatio: 2,
      });
      setStatus("idle");
      return dataUrl;
    } catch (err) {
      setStatus("error");
      return null;
    }
  }

  async function handleDownload() {
    const dataUrl = await captureImage();
    if (!dataUrl) return;
    const link = document.createElement("a");
    link.download = filename;
    link.href = dataUrl;
    link.click();
  }

  function handleShareToX() {
    const url = new URL("https://twitter.com/intent/tweet");
    url.searchParams.set("text", shareText);
    if (typeof window !== "undefined") {
      url.searchParams.set("url", window.location.href);
    }
    window.open(url.toString(), "_blank", "noopener,noreferrer");
  }

  return (
    <div className="flex flex-wrap gap-3">
      <button
        onClick={handleDownload}
        disabled={status === "working"}
        className="px-4 py-2 rounded-lg bg-gold text-navy font-semibold text-sm hover:bg-gold/90 transition-colors disabled:opacity-50"
      >
        {status === "working" ? "Preparing image..." : "Download card"}
      </button>
      <button
        onClick={handleShareToX}
        className="px-4 py-2 rounded-lg border border-white/20 text-ink-primary text-sm hover:border-gold hover:text-gold transition-colors"
      >
        Share on X
      </button>
      {status === "error" && (
        <span className="text-xs text-red-400 self-center">
          Couldn&apos;t generate the image — try again.
        </span>
      )}
    </div>
  );
}
