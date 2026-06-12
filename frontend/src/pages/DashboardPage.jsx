import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ItemCard from "@/components/ItemCard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ShieldCheck, ShieldOff, Plus } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState({ posts: [], claims: [] });

  useEffect(() => {
    api.get("/me/items").then((r) => setData(r.data)).catch(() => {});
  }, []);

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
          <div className="flex gap-3">
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
          <TabsList className="bg-em-bg border border-em-border rounded-full p-1">
            <TabsTrigger value="posts" data-testid="dashboard-tab-posts" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              My posts ({data.posts.length})
            </TabsTrigger>
            <TabsTrigger value="claims" data-testid="dashboard-tab-claims" className="rounded-full data-[state=active]:bg-em-primary data-[state=active]:text-white">
              My claims ({data.claims.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="posts" className="mt-6">
            {data.posts.length === 0 ? (
              <div className="em-card p-12 text-center text-em-textSoft">No posts yet.</div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.posts.map((i) => <ItemCard key={i.id} item={i} />)}
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
        </Tabs>
      </main>
      <Footer />
    </div>
  );
}
