import React from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Shield, Camera, KeyRound, MapPin, Flag, Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const STEPS = [
  { icon: Camera, title: "Take a clear photo", body: "Show the item with its expiration date clearly visible. Be honest about condition." },
  { icon: Shield, title: "AI safety screen", body: "Every post is auto-scanned by Claude AI to block prescription meds, alcohol, drugs, and weapons." },
  { icon: KeyRound, title: "4-digit claim code", body: "When someone claims, they get a code. You only mark the pickup complete after they show the code in person." },
  { icon: MapPin, title: "Meet in public", body: "Suggested meetups: grocery store parking lots, 7-Eleven, police station lobbies, public libraries." },
  { icon: Flag, title: "Report instantly", body: "Every item and user has a report button. 3 reports = manual review. Bad actors get banned." },
  { icon: Lock, title: "ID verification", body: "Posters and claimers verify their ID for $2 via Stripe. No anonymous bad actors." },
];

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">How it works</div>
        <h1 className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-4">Safe by design.</h1>
        <p className="text-em-textSoft text-lg max-w-2xl mb-10">
          ExpireMate connects neighbors before food spoils — but only with a strict safety stack between every interaction.
        </p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {STEPS.map((s, i) => (
            <div key={i} className="em-card p-6">
              <div className="w-11 h-11 rounded-xl bg-em-secondary text-white flex items-center justify-center mb-3">
                <s.icon className="w-5 h-5" />
              </div>
              <div className="font-heading text-lg font-semibold mb-1">{s.title}</div>
              <div className="text-sm text-em-textSoft leading-relaxed">{s.body}</div>
            </div>
          ))}
        </div>

        <div className="em-card p-8 bg-em-secondary text-white em-grain relative">
          <h2 className="font-heading text-3xl font-semibold mb-3">Ready to give your first item?</h2>
          <p className="opacity-90 mb-5 max-w-lg">Sign up, verify your ID for $2, and you're in. Your first post might feed a family this week.</p>
          <Link to="/register">
            <Button className="rounded-full bg-em-yellow hover:bg-em-yellow/90 text-em-text font-semibold h-11 px-6">
              Sign up free
            </Button>
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
