import { LiveMatchPage } from "@/components/live-match-page";
import { getLiveMatchSlots } from "@/lib/live-match";

export const dynamic = "force-dynamic";

export default async function Home() {
  const initialData = await getLiveMatchSlots();

  return <LiveMatchPage initialData={initialData} />;
}
