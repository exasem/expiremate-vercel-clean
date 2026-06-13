import React, { useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { StarRating } from "@/components/StarRating";
import { Star } from "lucide-react";
import { toast } from "sonner";

export default function ReviewModal({ itemId, counterpartyName, onSubmitted }) {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!rating) return toast.error("Pick a star rating");
    setSubmitting(true);
    try {
      await api.post(`/items/${itemId}/review`, { rating, text: text.trim() });
      toast.success("Review submitted, thank you!");
      setOpen(false);
      onSubmitted?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not submit");
    } finally { setSubmitting(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="review-open-button"
          className="rounded-full bg-em-yellow text-em-text hover:bg-em-yellow/90 font-semibold">
          <Star className="w-4 h-4 mr-1.5" /> Leave a review
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">Rate {counterpartyName}</DialogTitle>
          <DialogDescription>
            How was the pickup? Honest reviews keep the community safe.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-3 my-3">
          <StarRating value={rating} onChange={setRating} size={28} testId="review-stars" />
          <span className="font-heading text-2xl font-bold">{rating}/5</span>
        </div>

        <Textarea
          data-testid="review-text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Optional — what stood out? Be honest, be kind."
          className="rounded-xl border-em-border"
          maxLength={600}
        />

        <DialogFooter>
          <Button data-testid="review-submit-button" disabled={submitting} onClick={submit}
            className="rounded-full bg-em-primary hover:bg-em-primaryHover">
            {submitting ? "Submitting…" : "Submit review"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
