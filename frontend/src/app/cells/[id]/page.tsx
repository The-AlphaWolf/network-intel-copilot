import { CellDetailClient } from "./CellDetailClient";

export default async function CellDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CellDetailClient cellId={id} />;
}
