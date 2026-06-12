import React, { useEffect, useState, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function PaymentSuccessPage() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const type = params.get("type");
  const { refresh } = useAuth();
  const nav = useNavigate();
  const [state, setState] = useState({ status: "pending", message: "Confirming payment…" });
  const attempts = useRef(0);

  useEffect(() => {
    if (!sessionId) {
      setState({ status: "error", message: "No session id" });
      return;
    }
    let timer;
    const poll = async () => {
      attempts.current += 1;
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (data.payment_status === "paid") {
          setState({ status: "paid", message: type === "verify" ? "You're verified!" : "Donation received!", amount: data.amount, purpose: data.purpose });
          if (type === "verify") refresh();
          return;
        }
        if (data.status === "expired") {
          setState({ status: "expired", message: "Payment expired. Please try again." });
          return;
        }
        if (attempts.current >= 10) {
          setState({ status: "timeout", message: "Still processing… check your email." });
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch (e) {
        setState({ status: "error", message: "Could not verify payment status" });
      }
    };
    poll();
    return () => clearTimeout(timer);
    // eslint-disable-next-line
  }, [sessionId]);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-xl mx-auto px-4 py-16 w-full">
        <div data-testid="payment-status-card" className="em-card p-10 text-center">
          {state.status === "pending" && <Loader2 className="w-12 h-12 mx-auto text-em-primary animate-spin mb-4" />}
          {state.status === "paid" && <CheckCircle2 className="w-12 h-12 mx-auto text-em-secondary mb-4" />}
          {(state.status === "error" || state.status === "expired") && <XCircle className="w-12 h-12 mx-auto text-em-primary mb-4" />}

          <h1 className="font-heading text-3xl font-bold mb-2">{state.message}</h1>
          {state.status === "paid" && state.amount && (
            <p className="text-em-textSoft mb-6">${Number(state.amount).toFixed(2)} successfully processed.</p>
          )}

          {state.status === "paid" && type === "verify" && (
            <Button data-testid="payment-success-post-button" onClick={() => nav("/post")} className="rounded-full bg-em-primary hover:bg-em-primaryHover">
              Post your first item
            </Button>
          )}
          {state.status === "paid" && type === "donate" && (
            <Button data-testid="payment-success-home-button" onClick={() => nav("/")} className="rounded-full bg-em-primary hover:bg-em-primaryHover">
              Back to homepage
            </Button>
          )}
          {(state.status === "error" || state.status === "expired") && (
            <Button data-testid="payment-retry-button" onClick={() => nav(type === "verify" ? "/verify" : "/donate")} className="rounded-full bg-em-primary hover:bg-em-primaryHover">
              Try again
            </Button>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
