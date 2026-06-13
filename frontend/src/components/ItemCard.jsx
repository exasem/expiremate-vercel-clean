import React from "react";
import { Link } from "react-router-dom";
import { FILES_BASE } from "@/lib/api";
import { Clock, MapPin } from "lucide-react";

function daysUntil(iso) {
  if (!iso) return null;
  const target = new Date(iso);
  const now = new Date();
  const diff = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
  return diff;
}

function isFresh(createdIso) {
  if (!createdIso) return false;
  const created = new Date(createdIso);
  return (Date.now() - created.getTime()) < 2 * 60 * 60 * 1000; // <2h
}

export default function ItemCard({ item }) {
  const days = daysUntil(item.expiration_date);
  const urgent = days !== null && days <= 2;
  const expiredText =
    days === null ? "" :
    days < 0 ? `Expired ${Math.abs(days)}d ago` :
    days === 0 ? "Expires today" :
    days === 1 ? "Expires tomorrow" :
    `Expires in ${days} days`;

  return (
    <Link
      to={`/items/${item.id}`}
      data-testid={`item-card-${item.id}`}
      className="em-card overflow-hidden flex flex-col group"
    >
      <div className="relative h-48 bg-em-border overflow-hidden">
        {item.image_path ? (
          <img
            src={`${FILES_BASE}/${item.image_path}`}
            alt={item.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-em-textSoft text-sm">No photo</div>
        )}
        <div className="absolute top-3 left-3 flex gap-2">
          <span className="bg-white/95 text-xs font-medium px-2.5 py-1 rounded-full text-em-text">
            {item.category}
          </span>
          {isFresh(item.created_at) && (
            <span data-testid="fresh-badge" className="bg-em-primary text-white text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wide animate-pulse">
              Fresh
            </span>
          )}
        </div>
        {item.status !== "active" && (
          <div className="absolute top-3 right-3 bg-em-secondary text-white text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wide">
            {item.status}
          </div>
        )}
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <h3 className="font-heading font-semibold text-lg leading-snug line-clamp-2">{item.title}</h3>
        <div className="flex items-center gap-1.5 text-sm">
          <Clock className={`w-4 h-4 ${urgent ? "text-em-primary" : "text-em-textSoft"}`} />
          <span className={urgent ? "text-em-primary font-semibold" : "text-em-textSoft"}>{expiredText}</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm text-em-textSoft">
          <MapPin className="w-4 h-4" />
          <span>ZIP {item.zip_code}</span>
        </div>
      </div>
    </Link>
  );
}
