import React, { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      toast.success("Password updated! Please sign in.");
      nav("/login");
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Reset failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="em-card p-8 w-full max-w-md">
          <h1 className="font-heading text-2xl font-bold mb-2">Choose a new password</h1>
          {!token && <p className="text-em-primary text-sm mb-3">Missing token in URL.</p>}
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="pw">New password (min 6)</Label>
              <Input id="pw" type="password" required minLength={6} value={pw}
                onChange={(e) => setPw(e.target.value)}
                data-testid="reset-password-input" className="rounded-xl border-em-border" />
            </div>
            <Button data-testid="reset-submit-button" type="submit" disabled={loading || !token}
              className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-11 font-semibold">
              {loading ? "Updating…" : "Update password"}
            </Button>
          </form>
          <p className="mt-5 text-sm text-center"><Link to="/login" className="text-em-primary">Back to login</Link></p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
