import React from "react";
import { Star } from "lucide-react";

export function StarRating({ value = 0, size = 16, max = 5, onChange = null, testId = null }) {
  const interactive = !!onChange;
  return (
    <div className="inline-flex items-center gap-0.5" data-testid={testId}>
      {Array.from({ length: max }).map((_, i) => {
        const filled = i < Math.round(value);
        const StarEl = (
          <Star
            className={`${filled ? "fill-em-yellow text-em-yellow" : "text-em-border"} ${interactive ? "cursor-pointer hover:scale-110" : ""} transition-transform`}
            style={{ width: size, height: size }}
          />
        );
        return interactive ? (
          <button
            key={i}
            type="button"
            data-testid={testId ? `${testId}-${i + 1}` : undefined}
            onClick={() => onChange(i + 1)}
            className="p-0.5"
          >
            {StarEl}
          </button>
        ) : (
          <span key={i}>{StarEl}</span>
        );
      })}
    </div>
  );
}
