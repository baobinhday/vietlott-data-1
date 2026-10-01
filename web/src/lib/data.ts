// NDJSON data loaders for draw + prize data.
// The Next.js app sits at <repo>/web/ and the data lives at <repo>/data/.
// We resolve everything from process.cwd() to keep things simple.

import { readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import type { Draw, PrizeRecord, ProductConfig } from "./types";

/**
 * Resolve the on-disk data root. We try the following, in order:
 *   1. <repo>/data/  — when running from the repo root or web/ sub-folder.
 *   2. process.cwd()/data/ — fallback for dev environments.
 */
function dataRoot(): string {
  const candidates = [
    resolve(/*turbopackIgnore: true*/ process.cwd(), "..", "data"),
    resolve(/*turbopackIgnore: true*/ process.cwd(), "data"),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return candidates[0];
}

const drawCache = new Map<string, Draw[]>();
const prizeCache = new Map<string, PrizeRecord[]>();

function readNdjson(path: string): string[] {
  if (!existsSync(path)) return [];
  const text = readFileSync(path, "utf8");
  return text.split(/\r?\n/).filter((l) => l.trim().length > 0);
}

export function loadDraws(config: ProductConfig): Draw[] {
  const cached = drawCache.get(config.rawPath);
  if (cached) return cached;

  const path = join(dataRoot(), config.rawPath.split("/").pop()!);
  const lines = readNdjson(path);
  const draws: Draw[] = [];
  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      if (!Array.isArray(obj.result)) continue;
      draws.push({
        date: String(obj.date),
        id: String(obj.id),
        result: obj.result.map((n: unknown) => Number(n)),
        process_time: obj.process_time,
      });
    } catch {
      // skip malformed line
    }
  }
  // Sort newest first (matches Python's `descending=True` sort)
  draws.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : (a.id < b.id ? 1 : -1)));
  drawCache.set(config.rawPath, draws);
  return draws;
}

export function loadPrizes(config: ProductConfig): PrizeRecord[] {
  const key = `${config.rawPath}_prizes`;
  const cached = prizeCache.get(key);
  if (cached) return cached;

  const fileStem = config.name.replace("_", "");
  const path = join(dataRoot(), `${fileStem}_prizes.jsonl`);
  const lines = readNdjson(path);
  const records: PrizeRecord[] = [];
  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      if (!Array.isArray(obj.prizes)) continue;
      records.push({
        date: String(obj.date),
        id: String(obj.id),
        prizes: obj.prizes,
      });
    } catch {
      // skip malformed
    }
  }
  prizeCache.set(key, records);
  return records;
}

export function clearDataCache(): void {
  drawCache.clear();
  prizeCache.clear();
}
