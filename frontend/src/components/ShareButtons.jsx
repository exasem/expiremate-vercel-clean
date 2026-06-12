import React from "react";
import { Twitter, MessageCircle, Link as LinkIcon } from "lucide-react";
import { toast } from "sonner";

export default function ShareButtons({ title, itemId }) {
  const url = `${window.location.origin}/items/${itemId}`;
  const text = `I just claimed "${title}" on ExpireMate — free urgent giving from neighbors. Check it out:`;

  const copyLink = () => {
    navigator.clipboard.writeText(url);
    toast.success("Link copied");
  };

  return (
    <div className="flex items-center gap-2 mt-4">
      <span className="text-xs text-em-textSoft uppercase tracking-wider">Share</span>
      <a
        data-testid="share-twitter"
        href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`}
        target="_blank" rel="noreferrer"
        className="w-9 h-9 rounded-full border border-em-border flex items-center justify-center hover:border-em-primary hover:text-em-primary"
      >
        <Twitter className="w-4 h-4" />
      </a>
      <a
        data-testid="share-sms"
        href={`sms:?body=${encodeURIComponent(text + " " + url)}`}
        className="w-9 h-9 rounded-full border border-em-border flex items-center justify-center hover:border-em-primary hover:text-em-primary"
      >
        <MessageCircle className="w-4 h-4" />
      </a>
      <button
        data-testid="share-copy"
        onClick={copyLink}
        className="w-9 h-9 rounded-full border border-em-border flex items-center justify-center hover:border-em-primary hover:text-em-primary"
      >
        <LinkIcon className="w-4 h-4" />
      </button>
    </div>
  );
}
