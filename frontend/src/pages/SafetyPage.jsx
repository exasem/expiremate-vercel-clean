import React from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { AlertTriangle } from "lucide-react";

const RULES = [
  ["Always meet in a public place.", "Grocery store parking lots, libraries, police station lobbies. Never go to someone's home."],
  ["Never give or accept opened medicine.", "Sealed, unexpired over-the-counter only (Tylenol, Advil). No prescriptions, no opened bottles."],
  ["No alcohol, drugs, weapons, or adult products.", "ExpireMate is for food, sealed OTC meds, pet supplies, and cleaning items. Period."],
  ["Verify before you meet.", "Only deal with users who have a blue checkmark. Trust your gut — back out if something feels off."],
  ["Use the 4-digit claim code.", "Posters: only mark pickup complete after the claimer reads you the code. Claimers: only share the code at the meetup."],
  ["Report anything sketchy.", "Every item and user has a report button. 3 reports = manual review. Bad actors get banned permanently."],
  ["Minors — get parental consent.", "Users must be 18+ or have explicit parent permission. We cooperate with law enforcement when needed."],
];

export default function SafetyPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Safety</div>
        <h1 className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-4">Trust &amp; safety rules</h1>
        <p className="text-em-textSoft leading-relaxed mb-8">
          Read these before posting or claiming. By using ExpireMate you agree to follow them — and you accept full
          legal responsibility for items you post or claim.
        </p>

        <ol className="space-y-3 mb-12">
          {RULES.map(([t, b], i) => (
            <li key={i} className="em-card p-5">
              <div className="font-heading font-semibold text-lg mb-1">{i + 1}. {t}</div>
              <div className="text-sm text-em-textSoft">{b}</div>
            </li>
          ))}
        </ol>

        <div className="em-card p-6 bg-em-yellow/10 border-em-yellow/40 flex gap-3">
          <AlertTriangle className="w-6 h-6 text-em-yellow shrink-0 mt-0.5" />
          <p className="text-sm leading-relaxed">
            <strong>Disclaimer:</strong> ExpireMate is a platform that connects users. We do not inspect, test, or
            guarantee the safety of any item posted. All items are given "as is". You are solely responsible for any
            item you post or claim. ExpireMate cooperates fully with law enforcement. Report illegal activity
            immediately.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
