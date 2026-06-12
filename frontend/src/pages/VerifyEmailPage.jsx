import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [state, setState] = useState({ status: "pending", message: "Verifying your email…" });

  useEffect(() => {
    if (!token) {
      setState({ status: "error", message: "No verification token in URL." });
      return;
    }
    (async () => {
      try {
        await api.post("/auth/verify-email", { token });
        await refresh();
        setState({ status: "ok", message: "Email verified ✓" });
      } catch (e) {
        setState({ status: "error", message: e.response?.data?.detail || "Invalid token." });
      }
    })();
    // eslint-disable-next-line
  }, [token]);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div data-testid="verify-email-card" className="em-card p-10 w-full max-w-md text-center">
          {state.status === "pending" && <Loader2 className="w-12 h-12 mx-auto text-em-primary animate-spin mb-4" />}
          {state.status === "ok" && <CheckCircle2 className="w-12 h-12 mx-auto text-em-secondary mb-4" />}
          {state.status === "error" && <XCircle className="w-12 h-12 mx-auto text-em-primary mb-4" />}
          <h1 className="font-heading text-2xl font-bold mb-2">{state.message}</h1>
          <Link to="/dashboard"><Button className="rounded-full bg-em-primary hover:bg-em-primaryHover mt-3">Go to dashboard</Button></Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
