import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export default function WatchButton({ itemId }) {
  const { user } = useAuth();
  const [watching, setWatching] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get("/me/watchlist").then((r) => {
      setWatching(r.data.items.some((i) => i.id === itemId));
    }).catch(() => {});
  }, [user, itemId]);

  if (!user) return null;

  const toggle = async () => {
    setLoading(true);
    try {
      if (watching) {
        await api.delete(`/items/${itemId}/watch`);
        setWatching(false);
        toast.success("Removed from watchlist");
      } else {
        await api.post(`/items/${itemId}/watch`);
        setWatching(true);
        toast.success("Added to watchlist");
      }
    } catch (e) { toast.error("Could not update"); }
    finally { setLoading(false); }
  };

  return (
    <Button data-testid="watch-button" onClick={toggle} disabled={loading}
      variant="outline" size="sm"
      className="rounded-full border-em-border">
      {watching ? <><EyeOff className="w-4 h-4 mr-1" /> Watching</> : <><Eye className="w-4 h-4 mr-1" /> Watch</>}
    </Button>
  );
}
