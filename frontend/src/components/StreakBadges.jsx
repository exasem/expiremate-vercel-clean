import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function StreakBadges() {
  const [stats, setStats] = useState({ badges: [], total_rescued: 0, donations_count: 0 });

  useEffect(() => {
    api.get("/me/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  return (
    <div data-testid="streak-badges" className="em-card p-5 mb-6 bg-em-secondary/5 border-em-secondary/20">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-1">Your impact</div>
          <div className="font-heading text-2xl font-bold">
            {stats.total_rescued} item{stats.total_rescued !== 1 ? "s" : ""} rescued · {stats.donations_count} donation{stats.donations_count !== 1 ? "s" : ""}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {stats.badges.length === 0 ? (
            <span className="text-sm text-em-textSoft">Earn badges by posting and claiming items.</span>
          ) : stats.badges.map((b) => (
            <span key={b.key} className="bg-white border border-em-border rounded-full px-3 py-1.5 text-sm font-medium">
              <span className="mr-1">{b.emoji}</span>{b.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
