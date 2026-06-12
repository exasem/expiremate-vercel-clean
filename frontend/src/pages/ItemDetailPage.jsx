import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api, { FILES_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Clock, MapPin, Tag, ShieldCheck, AlertTriangle, Flag } from "lucide-react";
import { toast } from "sonner";

export default function ItemDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [item, setItem] = useState(null);
  const [claimCode, setClaimCode] = useState(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [reportReason, setReportReason] = useState("");

  const refresh = async () => {
    try {
      const { data } = await api.get(`/items/${id}`);
      setItem(data.item);
    } catch (e) { toast.error("Item not found"); }
  };

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [id]);

  const claim = async () => {
    if (!user) return nav("/login", { state: { from: `/items/${id}` } });
    if (!user.verified) return nav("/verify");
    try {
      const { data } = await api.post(`/items/${id}/claim`);
      setClaimCode(data.claim_code);
      toast.success("Claimed! Show your code at pickup.");
      refresh();
    } catch (e) { toast.error(e.response?.data?.detail || "Could not claim"); }
  };

  const confirmPickup = async () => {
    try {
      await api.post(`/items/${id}/confirm`, { code: confirmCode.trim() });
      toast.success("Pickup confirmed — donate to celebrate?");
      setConfirmCode("");
      nav("/donate");
    } catch (e) { toast.error(e.response?.data?.detail || "Bad code"); }
  };

  const submitReport = async () => {
    if (!user) return nav("/login");
    try {
      const fd = new FormData();
      fd.append("reason", reportReason);
      await api.post(`/items/${id}/report`, fd);
      toast.success("Report submitted. Thank you for keeping the community safe.");
      setReportReason("");
    } catch (e) { toast.error("Could not submit report"); }
  };

  if (!item) return (
    <div className="min-h-screen flex flex-col"><Navbar />
      <div className="flex-1 flex items-center justify-center text-em-textSoft">Loading…</div>
      <Footer />
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        <Link to="/browse" className="text-sm text-em-textSoft hover:text-em-primary mb-4 inline-block">← Back to browse</Link>
        <div className="grid md:grid-cols-2 gap-8">
          <div className="em-card overflow-hidden">
            {item.image_path ? (
              <img src={`${FILES_BASE}/${item.image_path}`} alt={item.title} className="w-full h-80 object-cover" />
            ) : (
              <div className="w-full h-80 bg-em-border" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-3 text-xs uppercase tracking-[0.2em] text-em-textSoft">
              <Tag className="w-4 h-4" /> {item.category}
              {item.status !== "active" && (
                <span className="ml-2 px-2 py-0.5 bg-em-secondary text-white rounded-full">{item.status}</span>
              )}
            </div>
            <h1 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mb-4">{item.title}</h1>
            <p className="text-em-textSoft mb-6 leading-relaxed">{item.description || "No description."}</p>

            <div className="space-y-2 mb-6 text-sm">
              <div className="flex items-center gap-2"><Clock className="w-4 h-4 text-em-primary" /> Expires: <strong>{item.expiration_date}</strong></div>
              <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-em-secondary" /> ZIP {item.zip_code}</div>
              <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-em-secondary" /> {item.meetup_suggestion}</div>
              <div className="text-em-textSoft">Quantity: {item.quantity} · Posted by {item.owner_name}</div>
            </div>

            {/* Actions */}
            {item.status === "active" && !item.is_owner && (
              <Button data-testid="claim-button" onClick={claim} className="rounded-full bg-em-primary hover:bg-em-primaryHover h-12 px-7 font-semibold w-full sm:w-auto">
                Claim this item
              </Button>
            )}

            {item.is_claimer && item.status === "claimed" && claimCode && (
              <div className="em-card p-5 mt-4 border-em-primary border-2">
                <div className="text-xs uppercase tracking-[0.2em] text-em-textSoft mb-1">Your claim code</div>
                <div data-testid="claim-code-display" className="font-heading text-5xl font-bold tracking-widest text-em-primary">{claimCode}</div>
                <div className="text-sm text-em-textSoft mt-2">Show this code to the poster at pickup.</div>
              </div>
            )}

            {item.is_owner && item.status === "claimed" && (
              <div className="em-card p-5 mt-4">
                <div className="font-heading font-semibold mb-2">Confirm pickup</div>
                <div className="text-sm text-em-textSoft mb-3">Ask the claimer for their 4-digit code:</div>
                <div className="flex gap-2">
                  <Input
                    value={confirmCode}
                    onChange={(e) => setConfirmCode(e.target.value)}
                    maxLength={4}
                    data-testid="confirm-code-input"
                    placeholder="0000"
                    className="rounded-xl text-center text-2xl tracking-widest font-bold border-em-border w-32"
                  />
                  <Button data-testid="confirm-code-button" onClick={confirmPickup} className="rounded-full bg-em-secondary hover:bg-em-secondaryHover">
                    Confirm
                  </Button>
                </div>
              </div>
            )}

            {item.status === "completed" && (
              <div className="em-card p-5 mt-4 border-em-secondary border-2">
                <div className="font-heading font-semibold text-em-secondary">Item rescued ✓</div>
                <div className="text-sm text-em-textSoft">This food/item was saved from the landfill. Thank you.</div>
              </div>
            )}

            {/* Report dialog */}
            <Dialog>
              <DialogTrigger asChild>
                <button data-testid="report-button" className="mt-6 flex items-center gap-1.5 text-xs text-em-textSoft hover:text-em-primary">
                  <Flag className="w-3.5 h-3.5" /> Report this item
                </button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle className="font-heading">Report this item</DialogTitle>
                  <DialogDescription>
                    Flag unsafe, illegal, or suspicious listings. The founder reviews every report.
                  </DialogDescription>
                </DialogHeader>
                <Textarea
                  data-testid="report-reason-input"
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  placeholder="What's wrong with this item?"
                  className="rounded-xl border-em-border"
                />
                <DialogFooter>
                  <Button data-testid="report-submit-button" onClick={submitReport} className="rounded-full bg-em-primary hover:bg-em-primaryHover">
                    Submit report
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <div className="mt-6 em-card p-4 bg-em-yellow/10 border-em-yellow/40 flex gap-3 text-sm">
              <AlertTriangle className="w-5 h-5 text-em-yellow shrink-0 mt-0.5" />
              <span>Always meet in public. Items are given "as is" — ExpireMate does not inspect or guarantee safety.</span>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
