import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import { toast } from "sonner";

function hexToUint8Array(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) out[i / 2] = parseInt(hex.substr(i, 2), 16);
  return out;
}

export default function BrowserPushOptIn({ zipCode }) {
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [supported, setSupported] = useState(true);

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setSupported(false);
      return;
    }
    navigator.serviceWorker.getRegistration().then((reg) => {
      if (!reg) return;
      reg.pushManager.getSubscription().then((sub) => setEnabled(!!sub));
    });
  }, []);

  const enable = async () => {
    setBusy(true);
    try {
      const { data: keyData } = await api.get("/push/vapid-public-key");
      const reg = await navigator.serviceWorker.register("/sw.js");
      const permission = await Notification.requestPermission();
      if (permission !== "granted") throw new Error("Permission denied");
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: hexToUint8Array(keyData.public_key_hex),
      });
      await api.post("/push/subscribe", {
        subscription: sub.toJSON(),
        zip_codes: zipCode ? [zipCode] : [],
      });
      setEnabled(true);
      toast.success("Browser alerts enabled");
    } catch (e) { toast.error(e.message || "Could not enable"); }
    finally { setBusy(false); }
  };

  if (!supported) return null;

  return (
    <Button data-testid="browser-push-button" onClick={enable} disabled={busy || enabled}
      variant="outline" className="rounded-full border-em-border">
      <Bell className="w-4 h-4 mr-1.5" />
      {enabled ? "Browser alerts on ✓" : busy ? "Enabling…" : "Enable browser alerts"}
    </Button>
  );
}
