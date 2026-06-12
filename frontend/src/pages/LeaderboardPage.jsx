import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Trophy, Heart } from "lucide-react";

export default function LeaderboardPage() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    api.get("/donations/leaderboard").then((r) => setRows(r.data.leaderboard)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Donor wall</div>
        <h1 className="font-heading text-4xl font-bold tracking-tight mb-2">The people powering this</h1>
        <p className="text-em-textSoft mb-8">Top contributors to the college fund. Thank you. ❤️</p>

        {rows.length === 0 ? (
          <div className="em-card p-12 text-center text-em-textSoft">
            <Heart className="w-10 h-10 mx-auto mb-3 text-em-primary" />
            No donations yet. Be the first to leave your mark.
          </div>
        ) : (
          <div className="em-card overflow-hidden divide-y divide-em-border">
            {rows.map((r, i) => (
              <div key={i} data-testid={`leaderboard-row-${i}`} className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-heading font-bold ${
                    i === 0 ? "bg-em-yellow text-em-text" :
                    i === 1 ? "bg-em-border text-em-text" :
                    i === 2 ? "bg-em-primary/20 text-em-primary" :
                    "bg-em-bg text-em-textSoft"
                  }`}>
                    {i < 3 ? <Trophy className="w-5 h-5" /> : i + 1}
                  </div>
                  <div>
                    <div className="font-semibold">{r.name}</div>
                    <div className="text-xs text-em-textSoft">{r.count} donation{r.count !== 1 ? "s" : ""}</div>
                  </div>
                </div>
                <div className="font-heading text-xl font-bold text-em-secondary">${r.total.toFixed(2)}</div>
              </div>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
