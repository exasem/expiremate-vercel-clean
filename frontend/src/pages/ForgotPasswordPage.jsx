import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setSent(true);
      if (data.dev_link) setDevLink(data.dev_link);
      toast.success("If that email exists, we sent a reset link.");
    } catch (ex) {
      toast.error("Could not send reset email");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="em-card p-8 w-full max-w-md">
          <h1 className="font-heading text-2xl font-bold mb-2">Forgot password?</h1>
          <p className="text-sm text-em-textSoft mb-5">We'll email you a link to choose a new one.</p>
          {!sent ? (
            <form onSubmit={submit} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" required value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="forgot-email-input" className="rounded-xl border-em-border" />
              </div>
              <Button data-testid="forgot-submit-button" disabled={loading} type="submit"
                className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-11 font-semibold">
                {loading ? "Sending…" : "Send reset link"}
              </Button>
            </form>
          ) : (
            <div className="text-sm space-y-3">
              <p>Check your inbox. The link expires in 1 hour.</p>
              {devLink && (
                <div className="em-card p-3 bg-em-yellow/10 border-em-yellow/40 text-xs break-all">
                  <strong>Dev mode link:</strong> <Link to={devLink.replace(/^https?:\/\/[^/]+/, "")} className="text-em-primary underline">{devLink}</Link>
                </div>
              )}
            </div>
          )}
          <div className="mt-5 text-sm text-center">
            <Link to="/login" className="text-em-primary font-semibold">Back to login</Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
