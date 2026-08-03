"use client";

import { useMemo } from "react";

interface NumberBallProps {
  value: number;
  variant?: "main" | "special" | "small" | "dim" | "hit";
  className?: string;
}

export function NumberBall({ value, variant = "main", className = "" }: NumberBallProps) {
  const cls = useMemo(() => {
    if (variant === "special") return "ball ball-small ball-special";
    if (variant === "small") return "ball ball-small";
    if (variant === "dim") return "ball ball-small ball-dim";
    if (variant === "hit") return "ball ball-small ball-hit";
    return "ball";
  }, [variant]);
  return <span className={`${cls} ${className}`}>{value.toString().padStart(2, "0")}</span>;
}

interface NumberRowProps {
  numbers: number[];
  highlight?: Set<number>;
  small?: boolean;
}

export function NumberRow({ numbers, highlight, small }: NumberRowProps) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {numbers.map((n, idx) => {
        const isHit = highlight?.has(n);
        const variant = isHit ? "hit" : small ? "small" : "main";
        return <NumberBall key={`${idx}-${n}`} value={n} variant={variant as NumberBallProps["variant"]} />;
      })}
    </span>
  );
}

interface TicketNumbersProps {
  main: number[];
  special: number | null;
  resultMain?: number[];
  resultSpecial?: number | null;
  size?: number;
  small?: boolean;
}

export function TicketNumbers({ main, special, resultMain, resultSpecial, small }: TicketNumbersProps) {
  const mainHit = useMemo(() => new Set(main.filter((n) => resultMain?.includes(n))), [main, resultMain]);
  const specialHit = !!special && special === resultSpecial;
  return (
    <span className="inline-flex items-center gap-2 flex-wrap">
      <NumberRow numbers={main} highlight={resultMain ? mainHit : undefined} small={small} />
      {special != null && (
        <span className="inline-flex items-center gap-1">
          <span className="text-zinc-600 text-xs">+</span>
          <NumberBall value={special} variant={specialHit ? "hit" : "special"} />
        </span>
      )}
    </span>
  );
}
