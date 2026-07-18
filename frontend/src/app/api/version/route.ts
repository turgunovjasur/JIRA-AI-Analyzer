import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse } from "next/server";

// Build ID — redeploy'da o'zgaradi. Client shu qiymatni kuzatib, o'zgarsa
// "yangi versiya" deb sahifani yangilaydi (eski bundle muammosini yo'qotadi).
// Manba: `.next/BUILD_ID` (Next build har safar yangi ID beradi). Topilmasa —
// jarayon boshlanganda bir marta yaratilgan nonce (konteyner restart signali).
const PROCESS_NONCE = `p-${Date.now().toString(36)}`;
let cachedBuildId: string | null = null;

async function resolveBuildId(): Promise<string> {
  if (cachedBuildId) return cachedBuildId;
  const candidates = [
    path.join(process.cwd(), ".next", "BUILD_ID"),
    path.join(process.cwd(), ".next", "standalone", ".next", "BUILD_ID"),
  ];
  for (const file of candidates) {
    try {
      const id = (await readFile(file, "utf8")).trim();
      if (id) {
        cachedBuildId = id;
        return id;
      }
    } catch {
      // keyingi nomzod
    }
  }
  cachedBuildId = process.env.NEXT_PUBLIC_BUILD_ID?.trim() || PROCESS_NONCE;
  return cachedBuildId;
}

export const dynamic = "force-dynamic";

export async function GET() {
  const buildId = await resolveBuildId();
  return NextResponse.json({ buildId }, { headers: { "Cache-Control": "no-store" } });
}
