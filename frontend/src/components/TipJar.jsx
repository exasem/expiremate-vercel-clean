import React, { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Heart, X } from "lucide-react";
import { toast } from "sonner";

export default function TipJar({ onDismiss }) {
  const [busy, setBusy] = useState(false);

  const donate = async (preset) => {
    setBusy(true);
    try {
      const { data } = await api.post("/payments/donate-checkout", {
        preset, origin_url: window.location.origin, anonymous: false,
      });
      window.location.href = data.url;
    } catch (e) {
      toast.error("Could not start tip checkout");
      setBusy(false);
    }
  };

  return (
    <div data-testid="tip-jar" className="em-card p-6 mt-6 relative bg-em-yellow/10 border-em-yellow/40">
      <button data-testid="tip-jar-dismiss" onClick={onDismiss}
        className="absolute top-3 right-3 text-em-textSoft hover:text-em-text">
        <X className="w-4 h-4" />
      </button>
      <div className="flex items-center gap-2 mb-2 text-em-secondary">
        <Heart className="w-5 h-5" />
        <span className="text-xs uppercase tracking-[0.2em] font-semibold">You just saved food. Nice.</span>
      </div>
      <h3 className="font-heading text-xl font-bold mb-2">Want to drop a tip to keep me in school?</h3>
      <p className="text-sm text-em-textSoft mb-4">
        Every dollar goes straight to my college fund. Even $1 helps.
      </p>
      <div className="flex gap-2 flex-wrap">
        {[["three", 3], ["five", 5], ["ten", 10]].map(([k, v]) => (
          <Button key={k} data-testid={`tip-jar-${v}`} disabled={busy}
            onClick={() => donate(k)}
            className="rounded-full bg-em-primary hover:bg-em-primaryHover font-semibold">
            Tip ${v}
          </Button>
        ))}
      </div>
    </div>
  );
}
