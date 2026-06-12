import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Leaf, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";

export default function ImpactCounter() {
  const [s, setS] = useState({ items_rescued_total: 0, items_rescued_week: 0, pounds_saved: 0 });

  useEffect(() => {
    const load = () => api.get("/stats/impact").then((r) => setS(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  return (
    <div data-testid="impact-counter" className="em-card relative em-grain overflow-hidden p-6 sm:p-8 bg-em-yellow text-em-text">
      <div className="grid sm:grid-cols-3 gap-4 sm:gap-6 relative">
        {[
          { v: s.items_rescued_total.toLocaleString(), l: "items rescued", icon: Leaf },
          { v: s.items_rescued_week.toLocaleString(), l: "this week", icon: TrendingUp },
          { v: `${s.pounds_saved.toLocaleString()} lbs`, l: "saved from landfill", icon: Leaf },
        ].map((row, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="flex flex-col"
          >
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] font-semibold mb-1 opacity-80">
              <row.icon className="w-3.5 h-3.5" />
              {row.l}
            </div>
            <div className="font-heading text-3xl sm:text-4xl font-bold tracking-tight">{row.v}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
