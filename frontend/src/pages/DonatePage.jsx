import React, { useState } from "react";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DonationThermometer from "@/components/DonationThermometer";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Heart, GraduationCap } from "lucide-react";

const PRESETS = [
  { key: "three", amount: 3 },
  { key: "five", amount: 5 },
  { key: "ten", amount: 10 },
];

export default function DonatePage() {
  const [preset, setPreset] = useState("five");
  const [custom, setCustom] = useState("");
  const [anon, setAnon] = useState(false);
  const [loading, setLoading] = useState(false);

  const donate = async () => {
    setLoading(true);
    try {
      const body = {
        preset,
        origin_url: window.location.origin,
        anonymous: anon,
      };
      if (preset === "custom") body.custom_amount = parseFloat(custom);
      const { data } = await api.post("/payments/donate-checkout", body);
      window.location.href = data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start checkout");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full grid md:grid-cols-2 gap-10">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Support the founder</div>
          <h1 className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Help me get to <span className="text-em-primary">college</span>.
          </h1>
          <p className="text-em-textSoft leading-relaxed mb-6">
            ExpireMate is free for everyone. Every dollar of every donation goes into the college fund —
            tuition, books, room & board. No paywalls, no premium, no ads.
          </p>
          <DonationThermometer compact />
        </div>

        <div className="em-card p-6 sm:p-8">
          <div className="flex items-center gap-2 mb-4 text-em-secondary">
            <GraduationCap className="w-6 h-6" />
            <div className="font-heading text-xl font-semibold">Pick an amount</div>
          </div>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                data-testid={`donate-preset-${p.amount}`}
                onClick={() => setPreset(p.key)}
                className={`h-14 rounded-2xl border font-heading text-xl font-bold transition-all ${
                  preset === p.key
                    ? "bg-em-primary text-white border-em-primary"
                    : "bg-white border-em-border hover:border-em-primary"
                }`}
              >
                ${p.amount}
              </button>
            ))}
          </div>

          <button
            onClick={() => setPreset("custom")}
            data-testid="donate-preset-custom"
            className={`w-full h-14 rounded-2xl border font-medium mb-2 ${
              preset === "custom" ? "border-em-primary bg-em-primary/5" : "border-em-border"
            }`}
          >
            Custom amount
          </button>
          {preset === "custom" && (
            <Input
              data-testid="donate-custom-amount"
              type="number" min="1" max="1000" step="0.5"
              value={custom}
              onChange={(e) => setCustom(e.target.value)}
              placeholder="Enter $ amount"
              className="rounded-xl border-em-border mb-2"
            />
          )}

          <label className="flex items-center gap-2 text-sm text-em-textSoft mt-3 mb-5 cursor-pointer">
            <Checkbox checked={anon} onCheckedChange={setAnon} data-testid="donate-anon-checkbox" />
            Donate anonymously (hide my name from the donor wall)
          </label>

          <Button
            data-testid="donate-submit-button"
            disabled={loading || (preset === "custom" && !custom)}
            onClick={donate}
            className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-12 font-semibold text-base"
          >
            <Heart className="w-4 h-4 mr-2" />
            {loading ? "Loading checkout…" : "Donate via Stripe"}
          </Button>
          <p className="text-xs text-em-textSoft mt-3 text-center">
            Secure card payment via Stripe. You'll be redirected.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
