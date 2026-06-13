import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api, { FILES_BASE } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { StarRating } from "@/components/StarRating";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, Ban, UserCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function ProfilePage() {
  const { userId } = useParams();
  const { user: me } = useAuth();
  const [data, setData] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [blocked, setBlocked] = useState(false);

  const refresh = async () => {
    const [p, r] = await Promise.all([
      api.get(`/users/${userId}/profile`),
      api.get(`/users/${userId}/reviews`),
    ]);
    setData(p.data);
    setReviews(r.data.reviews);
    if (me) {
      const { data: b } = await api.get("/me/blocks");
      setBlocked(b.blocks.some((x) => x.id === userId));
    }
  };

  useEffect(() => { refresh().catch(() => {}); /* eslint-disable-next-line */ }, [userId]);

  if (!data) return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <div className="flex-1 flex items-center justify-center text-em-textSoft">Loading…</div>
      <Footer />
    </div>
  );

  const toggleBlock = async () => {
    try {
      if (blocked) await api.delete(`/users/${userId}/block`);
      else await api.post(`/users/${userId}/block`);
      setBlocked(!blocked);
      toast.success(blocked ? "User unblocked" : "User blocked");
    } catch (e) { toast.error("Could not update"); }
  };

  const u = data.user;
  const isSelf = me && me.id === userId;

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="em-card p-6 sm:p-8 flex flex-col sm:flex-row gap-6 items-start mb-6">
          <Avatar className="w-24 h-24 border-2 border-em-border">
            {u.avatar_path && <AvatarImage src={`${FILES_BASE}/${u.avatar_path}`} alt={u.name} />}
            <AvatarFallback className="text-2xl font-heading bg-em-secondary text-white">
              {u.name?.[0]?.toUpperCase() || "?"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <h1 className="font-heading text-3xl font-bold tracking-tight">{u.name}</h1>
              {u.verified && (
                <Badge className="bg-em-secondary/15 text-em-secondary border-em-secondary/30" variant="outline">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1" /> Verified
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mb-2">
              <StarRating value={data.rating_avg || 0} />
              <span className="text-sm text-em-textSoft">
                {data.rating_avg ? `${data.rating_avg.toFixed(1)} · ${data.rating_count} review${data.rating_count !== 1 ? "s" : ""}` : "No reviews yet"}
              </span>
            </div>
            <div className="text-sm text-em-textSoft mb-3">
              {data.items_rescued} item{data.items_rescued !== 1 ? "s" : ""} rescued
            </div>
            {u.bio && <p className="text-sm text-em-text leading-relaxed">{u.bio}</p>}
          </div>
          <div className="flex flex-col gap-2">
            {isSelf ? (
              <Link to="/dashboard">
                <Button data-testid="profile-edit-button" variant="outline" className="rounded-full">Edit profile</Button>
              </Link>
            ) : me ? (
              <Button data-testid="profile-block-button" onClick={toggleBlock}
                variant={blocked ? "outline" : "outline"}
                className={`rounded-full ${blocked ? "border-em-border" : "border-em-primary text-em-primary"}`}>
                {blocked ? <><UserCheck className="w-4 h-4 mr-1.5" /> Unblock</> : <><Ban className="w-4 h-4 mr-1.5" /> Block</>}
              </Button>
            ) : null}
          </div>
        </div>

        <h2 className="font-heading text-2xl font-bold mb-4">Reviews</h2>
        {reviews.length === 0 ? (
          <div className="em-card p-10 text-center text-em-textSoft">No reviews yet.</div>
        ) : (
          <div className="space-y-3">
            {reviews.map((r) => (
              <div key={r.id} className="em-card p-4">
                <div className="flex items-center justify-between gap-3 mb-1">
                  <div className="flex items-center gap-2">
                    <Link to={`/users/${r.reviewer.id}`} className="font-semibold hover:text-em-primary">{r.reviewer.name}</Link>
                    <StarRating value={r.rating} size={14} />
                  </div>
                  <div className="text-xs text-em-textSoft">{r.created_at?.slice(0, 10)}</div>
                </div>
                {r.text && <p className="text-sm text-em-textSoft mt-1 leading-relaxed">{r.text}</p>}
              </div>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
