import React, { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageCircle, Send } from "lucide-react";

export default function ItemChat({ itemId, currentUserId }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/items/${itemId}/messages`);
      setMessages(data.messages);
    } catch (e) {}
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, [itemId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    try {
      const { data } = await api.post(`/items/${itemId}/messages`, { text: text.trim() });
      setMessages((m) => [...m, data.message]);
      setText("");
    } finally { setSending(false); }
  };

  return (
    <div className="em-card mt-6 overflow-hidden">
      <div className="px-4 py-3 border-b border-em-border flex items-center gap-2 bg-em-bg">
        <MessageCircle className="w-4 h-4 text-em-secondary" />
        <div className="font-heading font-semibold text-sm">Private chat with the other party</div>
      </div>
      <div className="px-4 py-3 max-h-72 overflow-y-auto space-y-2 bg-white">
        {messages.length === 0 && (
          <div className="text-sm text-em-textSoft py-6 text-center">
            No messages yet. Say hi to coordinate pickup — phone numbers are auto-redacted.
          </div>
        )}
        {messages.map((m) => {
          const mine = m.from_user_id === currentUserId;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                mine ? "bg-em-primary text-white rounded-br-sm" : "bg-em-bg text-em-text rounded-bl-sm border border-em-border"
              }`}>
                {!mine && <div className="text-[10px] uppercase tracking-wider opacity-70 mb-0.5">{m.from_name}</div>}
                {m.text}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={send} className="px-3 pt-2 pb-3 border-t border-em-border bg-em-bg">
        <div className="flex gap-1.5 mb-2 flex-wrap">
          {["On my way 🚗", "5 min out", "I'm here", "Can we meet tomorrow?", "Thanks!"].map((tpl) => (
            <button key={tpl} type="button"
              onClick={() => setText(tpl)}
              data-testid={`chat-quick-${tpl.slice(0, 5)}`}
              className="text-xs bg-white border border-em-border hover:border-em-primary hover:text-em-primary rounded-full px-2.5 py-1">
              {tpl}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <Input value={text} onChange={(e) => setText(e.target.value)}
            data-testid="chat-input" placeholder="Type a message…"
            className="rounded-full border-em-border bg-white" />
          <Button data-testid="chat-send-button" disabled={sending || !text.trim()}
            type="submit" className="rounded-full bg-em-secondary hover:bg-em-secondaryHover">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
