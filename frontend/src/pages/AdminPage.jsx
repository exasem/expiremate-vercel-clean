import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ItemCard from "@/components/ItemCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { ShieldCheck, Users, Flag, Mail, Package } from "lucide-react";

export default function AdminPage() {
  const { user, loading } = useAuth();
  const [overview, setOverview] = useState(null);
  const [reports, setReports] = useState([]);
  const [users, setUsers] = useState([]);
  const [emails, setEmails] = useState([]);

  const refresh = async () => {
    const [o, r, u, e] = await Promise.all([
      api.get("/admin/overview"),
      api.get("/admin/reports"),
      api.get("/admin/users"),
      api.get("/admin/emails"),
    ]);
    setOverview(o.data); setReports(r.data.reports);
    setUsers(u.data.users); setEmails(e.data.emails);
  };

  useEffect(() => { if (user?.role === "admin") refresh().catch(() => toast.error("Access denied")); }, [user]);

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;

  const ban = async (id) => { await api.post(`/admin/users/${id}/ban`); toast.success("User banned"); refresh(); };
  const unban = async (id) => { await api.post(`/admin/users/${id}/unban`); toast.success("User restored"); refresh(); };
  const removeItem = async (id) => { await api.delete(`/admin/items/${id}`); toast.success("Item removed"); refresh(); };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="flex items-center gap-2 mb-2 text-em-secondary">
          <ShieldCheck className="w-5 h-5" />
          <span className="text-xs uppercase tracking-[0.2em] font-semibold">Admin</span>
        </div>
        <h1 className="font-heading text-4xl font-bold tracking-tight mb-8">Control center</h1>

        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
            {[
              ["Users", overview.users, Users],
              ["Items", overview.items, Package],
              ["Active", overview.active_items, Package],
              ["Reports", overview.reports, Flag],
              ["Donations", overview.donations, ShieldCheck],
            ].map(([label, value, Icon], i) => (
              <div key={i} className="em-card p-5">
                <div className="flex items-center gap-2 text-em-textSoft text-xs uppercase tracking-wider mb-2">
                  <Icon className="w-4 h-4" />{label}
                </div>
                <div className="font-heading text-3xl font-bold">{value}</div>
              </div>
            ))}
          </div>
        )}

        <Tabs defaultValue="reports">
          <TabsList className="bg-em-bg border border-em-border rounded-full p-1 flex-wrap">
            <TabsTrigger value="reports" data-testid="admin-tab-reports" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">Reports</TabsTrigger>
            <TabsTrigger value="users" data-testid="admin-tab-users" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">Users</TabsTrigger>
            <TabsTrigger value="emails" data-testid="admin-tab-emails" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">Outbox</TabsTrigger>
          </TabsList>

          <TabsContent value="reports" className="mt-6 space-y-4">
            {reports.length === 0 && <div className="em-card p-12 text-center text-em-textSoft">No reports — community is healthy.</div>}
            {reports.map((r) => (
              <div key={r.id} className="em-card p-5 grid md:grid-cols-3 gap-5">
                <div className="md:col-span-2">
                  <div className="text-xs text-em-textSoft mb-1">{r.created_at} · reporter: {r.reporter_email}</div>
                  <div className="font-semibold mb-2">{r.reason}</div>
                  {r.item && <div className="text-sm text-em-textSoft">Item: <strong>{r.item.title}</strong> ({r.item.category}) · status {r.item.status}</div>}
                </div>
                <div className="flex items-center gap-2 md:justify-end">
                  {r.item && r.item.status !== "removed" && (
                    <Button data-testid={`admin-remove-item-${r.id}`} onClick={() => removeItem(r.item.id)} variant="outline" className="rounded-full">
                      Remove item
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="users" className="mt-6">
            <div className="em-card overflow-hidden divide-y divide-em-border">
              {users.map((u) => (
                <div key={u.id} className="p-4 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold truncate">{u.name} <span className="text-em-textSoft text-xs">· {u.email}</span></div>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {u.role === "admin" && <Badge className="bg-em-secondary">Admin</Badge>}
                      {u.verified && <Badge className="bg-em-secondary/15 text-em-secondary border-em-secondary/20" variant="outline">Verified</Badge>}
                      {u.banned && <Badge className="bg-em-primary">Banned</Badge>}
                    </div>
                  </div>
                  <div>
                    {u.role === "admin" ? null : u.banned ? (
                      <Button data-testid={`admin-unban-${u.id}`} variant="outline" className="rounded-full" onClick={() => unban(u.id)}>Restore</Button>
                    ) : (
                      <Button data-testid={`admin-ban-${u.id}`} className="rounded-full bg-em-primary hover:bg-em-primaryHover" onClick={() => ban(u.id)}>Ban</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="emails" className="mt-6 space-y-3">
            <p className="text-sm text-em-textSoft flex items-center gap-2"><Mail className="w-4 h-4" /> Dev mailbox — emails ExpireMate would have sent (Resend not wired yet).</p>
            {emails.length === 0 ? (
              <div className="em-card p-10 text-center text-em-textSoft">No emails yet.</div>
            ) : emails.map((e, i) => (
              <div key={i} className="em-card p-4">
                <div className="text-xs text-em-textSoft">{e.sent_at} → {e.to}</div>
                <div className="font-semibold mt-1">{e.subject}</div>
                <div className="text-sm text-em-textSoft mt-1">{e.body}</div>
                {e.link && <a href={e.link} className="text-em-primary text-sm break-all">{e.link}</a>}
              </div>
            ))}
          </TabsContent>
        </Tabs>
      </main>
      <Footer />
    </div>
  );
}
