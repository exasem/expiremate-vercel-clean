import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Bell, BellOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export default function ZipAlertButton({ zipCode }) {
  const { user } = useAuth();
  const [subbed, setSubbed] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user || !zipCode) return;
    api.get("/me/subscriptions").then((r) => setSubbed(r.data.zips.includes(zipCode))).catch(() => {});
  }, [user, zipCode]);

  if (!zipCode || !user) return null;

  const toggle = async () => {
    setLoading(true);
    try {
      if (subbed) {
        await api.delete(`/subscriptions/zip/${zipCode}`);
        setSubbed(false);
        toast.success(`Unsubscribed from ${zipCode}`);
      } else {
        await api.post("/subscriptions/zip", { zip_code: zipCode });
        setSubbed(true);
        toast.success(`You'll get email alerts for new items in ${zipCode}`);
      }
    } catch (e) { toast.error("Could not update"); }
    finally { setLoading(false); }
  };

  return (
    <Button
      data-testid="zip-alert-button"
      onClick={toggle}
      disabled={loading}
      variant="outline"
      className="rounded-full border-em-border h-11"
    >
      {subbed ? <BellOff className="w-4 h-4 mr-1.5" /> : <Bell className="w-4 h-4 mr-1.5" />}
      {subbed ? `Stop alerts for ${zipCode}` : `Alert me about ${zipCode}`}
    </Button>
  );
}
