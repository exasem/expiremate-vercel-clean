import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { GraduationCap, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export default function DonationThermometer({ compact = false }) {
  const [stats, setStats] = useState({ raised: 0, goal: 20000, donor_count: 0, percent: 0 });

  useEffect(() => {
    api.get("/donations/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const pct = Math.min(Math.max(stats.percent, 0), 100);

  return (
    <div
      data-testid="donation-thermometer"
      className={`relative overflow-hidden em-grain rounded-2xl border border-em-border bg-em-secondary text-white p-6 ${
        compact ? "" : "sm:p-8"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] opacity-80 mb-1">College Fund</div>
          <div className="font-heading text-2xl sm:text-3xl font-bold leading-tight">
            ${stats.raised.toLocaleString(undefined, { minimumFractionDigits: 0 })}
            <span className="opacity-60 font-medium text-base"> / ${stats.goal.toLocaleString()}</span>
          </div>
        </div>
        <div className="bg-em-yellow text-em-text rounded-full w-12 h-12 flex items-center justify-center shrink-0">
          <GraduationCap className="w-6 h-6" />
        </div>
      </div>

      <div className="relative h-5 rounded-full bg-white/15 overflow-hidden mb-3">
        <div
          className="h-full em-thermo-stripes bg-em-yellow transition-all duration-700"
          style={{ width: `${pct}%` }}
          data-testid="thermo-fill"
        />
      </div>

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 opacity-90">
          <TrendingUp className="w-4 h-4" />
          <span>{stats.donor_count} donors · {pct.toFixed(1)}% funded</span>
        </div>
        {!compact && (
          <Link to="/donate">
            <Button
              data-testid="thermo-donate-button"
              className="bg-em-primary hover:bg-em-primaryHover rounded-full px-5 h-9 text-sm font-semibold"
            >
              Donate
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
