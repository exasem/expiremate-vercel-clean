import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Sprout } from "lucide-react";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function LoginPage() {
  const { login, formatApiError } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back!");
      const to = loc.state?.from || "/dashboard";
      nav(to);
    } catch (ex) {
      setErr(formatApiError(ex.response?.data?.detail) || ex.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md em-card p-8">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-em-primary flex items-center justify-center text-white">
              <Sprout className="w-5 h-5" />
            </div>
            <div className="font-heading text-2xl font-bold">Welcome back</div>
          </div>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email-input"
                className="rounded-xl border-em-border"
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password" type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password-input"
                className="rounded-xl border-em-border"
              />
            </div>
            {err && <div data-testid="login-error" className="text-sm text-em-primary">{err}</div>}
            <Button
              type="submit" disabled={loading}
              data-testid="login-submit-button"
              className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-11 font-semibold"
            >
              {loading ? "Signing in…" : "Log in"}
            </Button>
          </form>
          <p className="mt-5 text-sm text-em-textSoft text-center">
            <Link to="/forgot-password" data-testid="login-forgot-link" className="text-em-textSoft hover:text-em-primary underline">
              Forgot your password?
            </Link>
          </p>
          <p className="mt-3 text-sm text-em-textSoft text-center">
            No account yet?{" "}
            <Link to="/register" data-testid="login-register-link" className="text-em-primary font-semibold">
              Sign up free
            </Link>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
