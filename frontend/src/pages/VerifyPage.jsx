import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { ShieldCheck, Check } from "lucide-react";
import { toast } from "sonner";

export default function VerifyPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [loading, setLoading] = useState(false);

  const startCheckout = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/payments/identity-checkout", { origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start verification");
      setLoading(false);
    }
  };

  if (user?.verified) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-2xl mx-auto px-4 py-16 w-full">
          <div className="em-card p-8 text-center">
            <ShieldCheck className="w-12 h-12 text-em-secondary mx-auto mb-3" />
            <h1 className="font-heading text-3xl font-bold mb-2">You're verified ✓</h1>
            <p className="text-em-textSoft mb-6">Your blue checkmark is active. Post or claim away.</p>
            <Button onClick={() => nav("/post")} className="rounded-full bg-em-primary hover:bg-em-primaryHover">
              Post your first item
            </Button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Safety first</div>
        <h1 className="font-heading text-4xl font-bold tracking-tight mb-3">Verify your ID</h1>
        <p className="text-em-textSoft mb-8">
          Upload your driver's license or state ID via Stripe Identity. ExpireMate never sees the document —
          Stripe verifies it and we just see "verified ✓". Verified posters and claimers get a blue checkmark.
        </p>

        <div className="em-card p-6 mb-6">
          <div className="font-heading text-lg font-semibold mb-3">What you get</div>
          <ul className="space-y-2 text-sm">
            {[
              "Blue verified checkmark on your profile",
              "Ability to post items and claim items",
              "Stripe Identity selfie + ID document verification",
              "Trust from neighbors at pickup",
            ].map((t) => (
              <li key={t} className="flex items-start gap-2">
                <Check className="w-4 h-4 text-em-secondary mt-0.5 shrink-0" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>

        <Button
          data-testid="verify-checkout-button"
          disabled={loading}
          onClick={startCheckout}
          className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-12 font-semibold text-base"
        >
          {loading ? "Loading…" : "Verify ID via Stripe Identity"}
        </Button>
        <p className="text-xs text-em-textSoft mt-3 text-center">
          Secure verification via Stripe Identity. You'll be redirected.
        </p>
      </main>
      <Footer />
    </div>
  );
}
