import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Upload, ShieldCheck } from "lucide-react";

const CATS = ["Food", "Sealed Medicine", "Pet", "Cleaning", "Other"];

export default function PostItemPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    title: "", description: "", category: "Food",
    expiration_date: "", quantity: "1", zip_code: user?.zip_code || "",
    meetup_suggestion: "",
  });
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user && !user.verified) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-2xl mx-auto px-4 py-16 w-full">
          <div className="em-card p-8 text-center">
            <ShieldCheck className="w-12 h-12 text-em-secondary mx-auto mb-4" />
            <h1 className="font-heading text-3xl font-bold mb-2">Verify your ID to post</h1>
            <p className="text-em-textSoft mb-6">
              A one-time $2 ID check keeps everyone safe — and 100% of it goes to the college fund.
            </p>
            <Button data-testid="post-verify-cta" onClick={() => nav("/verify")} className="rounded-full bg-em-primary hover:bg-em-primaryHover h-11 px-6 font-semibold">
              Verify ID — $2
            </Button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const onPhoto = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPhoto(f);
    setPreview(URL.createObjectURL(f));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!photo) return toast.error("Photo is required");
    setSubmitting(true);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => fd.append(k, v));
      fd.append("photo", photo);
      const { data } = await api.post("/items", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Item posted! 🎉");
      nav(`/items/${data.item.id}`);
    } catch (ex) {
      toast.error(ex.response?.data?.detail || "Failed to post");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Give it away</div>
        <h1 className="font-heading text-4xl font-bold tracking-tight mb-8">Post an item</h1>

        <form onSubmit={submit} className="em-card p-6 sm:p-8 space-y-5">
          <div>
            <Label>Photo (required)</Label>
            <label htmlFor="photo" className="block mt-1 border-2 border-dashed border-em-border rounded-2xl p-6 cursor-pointer hover:border-em-primary transition-colors text-center">
              {preview ? (
                <img src={preview} alt="preview" className="mx-auto max-h-48 rounded-xl" />
              ) : (
                <div className="flex flex-col items-center gap-2 text-em-textSoft">
                  <Upload className="w-7 h-7" />
                  <div className="text-sm">Click to upload a clear photo of the item</div>
                </div>
              )}
              <input id="photo" data-testid="post-photo-input" type="file" accept="image/*" className="hidden" onChange={onPhoto} />
            </label>
          </div>

          <div>
            <Label htmlFor="title">Item name</Label>
            <Input id="title" required value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              data-testid="post-title-input" className="rounded-xl border-em-border" />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <Label>Category</Label>
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                <SelectTrigger data-testid="post-category-select" className="rounded-xl border-em-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="exp">Expiration date</Label>
              <Input id="exp" type="date" required value={form.expiration_date}
                onChange={(e) => setForm({ ...form, expiration_date: e.target.value })}
                data-testid="post-expiration-input" className="rounded-xl border-em-border" />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="qty">Quantity</Label>
              <Input id="qty" value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                data-testid="post-quantity-input" className="rounded-xl border-em-border" />
            </div>
            <div>
              <Label htmlFor="zip">ZIP code</Label>
              <Input id="zip" required value={form.zip_code}
                onChange={(e) => setForm({ ...form, zip_code: e.target.value })}
                data-testid="post-zip-input" className="rounded-xl border-em-border" />
            </div>
          </div>

          <div>
            <Label htmlFor="desc">Description (optional)</Label>
            <Textarea id="desc" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              data-testid="post-description-input" className="rounded-xl border-em-border"
              placeholder="Condition, brand, anything useful for the neighbor to know" />
          </div>

          <div>
            <Label htmlFor="meet">Suggested public meetup (optional)</Label>
            <Input id="meet" value={form.meetup_suggestion}
              onChange={(e) => setForm({ ...form, meetup_suggestion: e.target.value })}
              data-testid="post-meetup-input" className="rounded-xl border-em-border"
              placeholder="e.g., 7-Eleven on Main St parking lot" />
          </div>

          <Button type="submit" disabled={submitting}
            data-testid="post-submit-button"
            className="w-full rounded-full bg-em-primary hover:bg-em-primaryHover h-12 font-semibold">
            {submitting ? "Posting…" : "Post item"}
          </Button>
          <p className="text-xs text-em-textSoft text-center">
            Posts are auto-screened by AI before going live. Prohibited items are blocked.
          </p>
        </form>
      </main>
      <Footer />
    </div>
  );
}
