import React, { useEffect, useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";

export default function IdentityReturnPage() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [state, setState] = useState({ status: "loading", error: null });

  useEffect(() => {
    if (!sessionId) { setState({ status: "loading", error: "No session id" }); return; }
    let timer;
    let attempts = 0;
    const poll = async () => {
      attempts += 1;
      try {
        const { data } = await api.get(`/payments/identity-status/${sessionId}`);
        setState({ status: data.status, error: data.last_error });
        if (data.status === "verified") { refresh(); return; }
        if (data.status === "canceled" || attempts >= 10) return;
        timer = setTimeout(poll, 3000);
      } catch (e) { setState({ status: "error", error: e.response?.data?.detail || "Failed" }); }
    };
    poll();
    return () => clearTimeout(timer);
    // eslint-disable-next-line
  }, [sessionId]);

  const map = {
    verified: { icon: CheckCircle2, color: "text-em-secondary", title: "You're verified ✓",
                body: "Your blue checkmark is now active. Post or claim anything.", cta: "Post your first item", to: "/post" },
    processing: { icon: Loader2, color: "text-em-primary animate-spin", title: "Verification processing…",
                  body: "Stripe is reviewing your documents. This usually takes under 5 minutes." },
    requires_input: { icon: XCircle, color: "text-em-primary", title: "Needs another try",
                      body: "Your document didn't pass. Please restart the verification.", cta: "Try again", to: "/verify" },
    canceled: { icon: XCircle, color: "text-em-primary", title: "Verification canceled",
                body: "No worries — restart any time.", cta: "Restart", to: "/verify" },
    loading: { icon: Loader2, color: "text-em-primary animate-spin", title: "Checking your verification…", body: "" },
    error: { icon: XCircle, color: "text-em-primary", title: "Something went wrong",
             body: "Try again from the verify page.", cta: "Go to verify", to: "/verify" },
  };
  const view = map[state.status] || map.loading;
  const Icon = view.icon;

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-xl mx-auto px-4 py-16 w-full">
        <div data-testid="identity-return-card" className="em-card p-10 text-center">
          <Icon className={`w-12 h-12 mx-auto mb-4 ${view.color}`} />
          <h1 className="font-heading text-3xl font-bold mb-2">{view.title}</h1>
          <p className="text-em-textSoft mb-6">{view.body}</p>
          {view.cta && (
            <Button data-testid="identity-return-cta" onClick={() => nav(view.to)}
              className="rounded-full bg-em-primary hover:bg-em-primaryHover">{view.cta}</Button>
          )}
          {!view.cta && state.status === "processing" && (
            <Link to="/dashboard" className="text-em-primary text-sm">Back to dashboard</Link>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
