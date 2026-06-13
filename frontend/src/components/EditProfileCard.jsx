import React, { useEffect, useState } from "react";
import api, { FILES_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Upload } from "lucide-react";
import { toast } from "sonner";

export default function EditProfileCard() {
  const { user, refresh } = useAuth();
  const [bio, setBio] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => { if (user) setBio(user.bio || ""); }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/me/profile", { bio });
      await refresh();
      toast.success("Profile saved");
    } catch (e) { toast.error("Could not save"); }
    finally { setSaving(false); }
  };

  const upload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("photo", f);
      await api.post("/me/avatar", fd, { headers: { "Content-Type": "multipart/form-data" } });
      await refresh();
      toast.success("Avatar updated");
    } catch (e) { toast.error("Upload failed"); }
    finally { setUploading(false); }
  };

  if (!user) return null;

  return (
    <div className="em-card p-6 mb-6">
      <div className="flex items-center gap-4 mb-4">
        <Avatar className="w-16 h-16 border border-em-border">
          {user.avatar_path && <AvatarImage src={`${FILES_BASE}/${user.avatar_path}`} />}
          <AvatarFallback className="text-xl font-heading bg-em-secondary text-white">{user.name?.[0]?.toUpperCase()}</AvatarFallback>
        </Avatar>
        <label className="inline-flex items-center gap-1.5 text-sm cursor-pointer border border-em-border rounded-full px-3 py-1.5 hover:border-em-primary">
          <Upload className="w-3.5 h-3.5" />
          {uploading ? "Uploading…" : "Change avatar"}
          <input data-testid="avatar-input" type="file" accept="image/*" className="hidden" onChange={upload} />
        </label>
      </div>
      <label className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-1 block">Bio</label>
      <Textarea data-testid="profile-bio-input" value={bio} maxLength={500}
        onChange={(e) => setBio(e.target.value)}
        placeholder="A line or two about you — what you like to give away, what your neighborhood is like."
        className="rounded-xl border-em-border" />
      <Button data-testid="profile-save-button" onClick={save} disabled={saving}
        className="mt-3 rounded-full bg-em-primary hover:bg-em-primaryHover">
        {saving ? "Saving…" : "Save profile"}
      </Button>
    </div>
  );
}
