import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Sprout } from "lucide-react";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function RegisterPage() {
  const { register, formatApiError } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", zip_code: "" });
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!agree) return setErr("You must agree to the safety disclaimer.");
    setErr("");
    setLoading(true);
    try {
      await register(form);
      toast.success("Account created! Now verify your ID to post or claim.");
      nav("/verify");
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
            <div className="w-10 h-10 rounded-xl bg-em-secondary flex items-center justify-center text-white">
              <Sprout className="w-5 h-5" />
            </div>
            <div className="font-heading text-2xl font-bold">Join ExpireMate</div>
          </div>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label htmlFor="name">Full name</Label>
              <Input id="name" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="register-name-input" className="rounded-xl border-em-border" />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                data-testid="register-email-input" className="rounded-xl border-em-border" />
            </div>
            <div>
              <Label htmlFor="password">Password (min 6 chars)</Label>
              <Input id="password" type="password" required minLength={6} value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                data-testid="register-password-input" className="rounded-xl border-em-border" />
            </div>
            <div>
              <Label htmlFor="zip">ZIP code</Label>
              <Input id="zip" required value={form.zip_code}
                onChange={(e) => setForm({ ...form, zip_code: e.target.value })}
                data-testid="register-zip-input" className="rounded-xl border-em-border" />
            </div>
            <div className="flex items-start gap-2 text-sm text-em-textSoft">
              <Checkbox checked={agree} onCheckedChange={(v) => setAgree(!!v)} id="register-disclaimer" data-testid="register-disclaimer-checkbox" className="mt-0.5" />
              <label htmlFor="register-disclaimer" className="cursor-pointer">
                I am 18+ (or have parental consent) and I take full responsibility for items I post or claim.
                I will meet in public places only.
              </label>
            </div>
            {err && <div data-testid="register-error" className="text-sm text-em-primary">{err}</div>}
            <Button type="submit" disabled={loading}
              data-testid="register-submit-button"
              className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-11 font-semibold">
              {loading ? "Creating account…" : "Create account"}
            </Button>
          </form>
          <p className="mt-5 text-sm text-em-textSoft text-center">
            Already have an account?{" "}
            <Link to="/login" className="text-em-primary font-semibold">Log in</Link>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
