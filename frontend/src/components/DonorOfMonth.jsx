import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Crown } from "lucide-react";

export default function DonorOfMonth() {
  const [d, setD] = useState({ name: null, total: 0 });

  useEffect(() => {
    api.get("/stats/donor-of-month").then((r) => setD(r.data)).catch(() => {});
  }, []);

  if (!d.name) return null;

  return (
    <div data-testid="donor-of-month" className="em-card p-5 bg-em-yellow/15 border-em-yellow/40">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-em-yellow flex items-center justify-center">
          <Crown className="w-6 h-6 text-em-text" />
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft">Donor of the month</div>
          <div className="font-heading text-xl font-bold">
            {d.name} <span className="text-em-textSoft text-sm font-medium">· ${d.total.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
