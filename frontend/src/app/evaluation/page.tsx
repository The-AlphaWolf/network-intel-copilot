"use client";

import { useEffect, useState } from "react";
import { getEvaluation, EvaluationResponse } from "@/lib/api";
import { Card, CardHeader, KpiTile, EmptyState } from "@/components/ui";

export default function EvaluationPage() {
  const [data, setData] = useState<EvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvaluation().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">{error}</div>;

  const metrics = data?.metrics as Record<string, number> | undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Evaluation</h1>
        <p className="text-sm text-text-dim">Retrieval quality, citation correctness, faithfulness, and root-cause accuracy against ground truth.</p>
      </div>

      {!data ? (
        <EmptyState message="Loading..." />
      ) : data.status === "not_run" ? (
        <Card className="p-6 text-center">
          <p className="text-sm text-text-dim">{data.message}</p>
          <code className="mt-3 inline-block rounded bg-surface-2 px-3 py-1.5 font-mono text-xs text-cyan">python -m app.eval.run_eval</code>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <KpiTile label="Recall@5" value={metrics?.recall_at_5 !== undefined ? `${(metrics.recall_at_5 * 100).toFixed(0)}%` : "-"} />
            <KpiTile label="Citation Correctness" value={metrics?.citation_correctness !== undefined ? `${(metrics.citation_correctness * 100).toFixed(0)}%` : "-"} />
            <KpiTile label="Faithfulness" value={metrics?.faithfulness !== undefined ? `${(metrics.faithfulness * 100).toFixed(0)}%` : "-"} />
            <KpiTile label="Root Cause Accuracy" value={metrics?.root_cause_top1_accuracy !== undefined ? `${(metrics.root_cause_top1_accuracy * 100).toFixed(0)}%` : "-"} />
          </div>
          <Card>
            <CardHeader title="Raw Results" />
            <pre className="overflow-x-auto p-4 text-xs text-text-dim">{JSON.stringify(data, null, 2)}</pre>
          </Card>
        </>
      )}
    </div>
  );
}
