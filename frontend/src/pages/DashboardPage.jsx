import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ItemCard from "@/components/ItemCard";
import StreakBadges from "@/components/StreakBadges";
import BrowserPushOptIn from "@/components/BrowserPushOptIn";
import EditProfileCard from "@/components/EditProfileCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ShieldCheck, ShieldOff, Plus, Download, Mail } from "lucide-react";
import { API } from "@/lib/api";
import { toast } from "sonner";

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState({ posts: [], claims: [] });
  const [donations, setDonations] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [sendingVerify, setSendingVerify] = useState(false);

  useEffect(() => {
    api.get("/me/items").then((r) => setData(r.data)).catch(() => {});
    api.get("/me/donations").then((r) => setDonations(r.data.donations)).catch(() => {});
    api.get("/me/watchlist").then((r) => setWatchlist(r.data.items)).catch(() => {});
  }, []);

  const sendEmailVerify = async () => {
    setSendingVerify(true);
    try {
      const { data: r } = await api.post("/auth/send-verification");
      if (r.already_verified) toast.success("Email already verified.");
      else toast.success("Verification email sent! (Check the admin Outbox in dev mode.)");
    } catch (e) { toast.error("Could not send"); }
    finally { setSendingVerify(false); }
  };

  const bumpItem = async (id) => {
    try {
      await api.post(`/items/${id}/bump`);
      toast.success("Bumped to the top!");
    } catch (e) { toast.error(e.response?.data?.detail || "Could not bump"); }
  };

  const downloadReceipt = (sid) => {
    const token = localStorage.getItem("em_token");
    const url = `${API}/donations/${sid}/receipt${token ? `?_=${Date.now()}` : ""}`;
    fetch(url, { credentials: "include", headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((res) => res.ok ? res.blob() : Promise.reject(res))
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `expiremate-receipt-${sid.slice(0, 10)}.pdf`;
        a.click();
      })
      .catch(() => toast.error("Could not download receipt"));
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="flex items-start justify-between gap-4 flex-wrap mb-8">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-1">Dashboard</div>
            <h1 className="font-heading text-4xl font-bold tracking-tight">Hi, {user?.name?.split(" ")[0]}</h1>
            <p className="text-em-textSoft mt-1">
              {user?.verified ? (
                <span className="inline-flex items-center gap-1 text-em-secondary"><ShieldCheck className="w-4 h-4" /> Verified member</span>
              ) : (
                <span className="inline-flex items-center gap-1 text-em-primary"><ShieldOff className="w-4 h-4" /> Not verified yet</span>
              )}
            </p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <BrowserPushOptIn zipCode={user?.zip_code} />
            {!user?.email_verified && (
              <Button data-testid="dashboard-send-email-verify"
                onClick={sendEmailVerify} disabled={sendingVerify}
                variant="outline" className="rounded-full border-em-border">
                <Mail className="w-4 h-4 mr-1" />
                {sendingVerify ? "Sending…" : "Verify email"}
              </Button>
            )}
            {!user?.verified && (
              <Link to="/verify">
                <Button data-testid="dashboard-verify-button" className="rounded-full bg-em-secondary hover:bg-em-secondaryHover text-white">
                  Verify ID — $2
                </Button>
              </Link>
            )}
            <Link to="/post">
              <Button data-testid="dashboard-post-button" className="rounded-full bg-em-primary hover:bg-em-primaryHover font-semibold">
                <Plus className="w-4 h-4 mr-1" /> Post an item
              </Button>
            </Link>
          </div>
        </div>

        <Tabs defaultValue="posts">
          <StreakBadges />
          <EditProfileCard />
          <TabsList className="bg-em-bg border border-em-border rounded-full p-1">
            <TabsTrigger value="posts" data-testid="dashboard-tab-posts" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              My posts ({data.posts.length})
            </TabsTrigger>
            <TabsTrigger value="claims" data-testid="dashboard-tab-claims" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              My claims ({data.claims.length})
            </TabsTrigger>
            <TabsTrigger value="donations" data-testid="dashboard-tab-donations" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              Donations ({donations.length})
            </TabsTrigger>
            <TabsTrigger value="watchlist" data-testid="dashboard-tab-watchlist" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              Watchlist ({watchlist.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="posts" className="mt-6">
            {data.posts.length === 0 ? (
              <div className="em-card p-12 text-center text-em-textSoft">No posts yet.</div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.posts.map((i) => (
                  <div key={i.id} className="flex flex-col">
                    <ItemCard item={i} />
                    {i.status === "active" && (
                      <Button data-testid={`bump-item-${i.id}`}
                        onClick={() => bumpItem(i.id)}
                        variant="outline"
                        className="rounded-full mt-2 border-em-border text-em-textSoft hover:text-em-primary">
                        ⬆ Bump to top (once / 24h)
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="claims" className="mt-6">
            {data.claims.length === 0 ? (
              <div className="em-card p-12 text-center text-em-textSoft">No claims yet — go grab something!</div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.claims.map((i) => <ItemCard key={i.id} item={i} />)}
              </div>
            )}
          </TabsContent>

          <TabsContent value="donations" className="mt-6">
            {donations.length === 0 ? (
              <div className="em-card p-12 text-center text-em-textSoft">No donations yet — <Link to="/donate" className="text-em-primary font-semibold">support the founder</Link>.</div>
            ) : (
              <div className="em-card divide-y divide-em-border">
                {donations.map((d) => (
                  <div key={d.session_id} data-testid={`donation-row-${d.session_id}`} className="p-4 flex items-center justify-between gap-3">
                    <div>
                      <div className="font-heading text-lg font-semibold">${d.amount.toFixed(2)} <span className="text-xs text-em-textSoft uppercase">{d.currency}</span></div>
                      <div className="text-xs text-em-textSoft">{d.paid_at}</div>
                    </div>
                    <Button data-testid={`donation-receipt-${d.session_id}`}
                      onClick={() => downloadReceipt(d.session_id)}
                      variant="outline" className="rounded-full border-em-border">
                      <Download className="w-4 h-4 mr-1" /> Receipt
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="watchlist" className="mt-6">
            {watchlist.length === 0 ? (
              <div className="em-card p-12 text-center text-em-textSoft">
                No watched items yet — tap the eye icon on any item to follow it.
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {watchlist.map((i) => <ItemCard key={i.id} item={i} />)}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
      <Footer />
    </div>
  );
}
