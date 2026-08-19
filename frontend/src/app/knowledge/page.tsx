"use client";

import { useEffect, useState } from "react";
import { listDocuments, searchKnowledge, KbDocument, KbSearchResult } from "@/lib/api";
import { Card, CardHeader, EmptyState, Badge } from "@/components/ui";
import { Search, FileText, Loader2 } from "lucide-react";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KbSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments().then(setDocs).catch((e) => setError(e.message));
  }, []);

  async function runSearch() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      setResults(await searchKnowledge(query, 6));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text">Knowledge Base</h1>
        <p className="text-sm text-text-dim">Synthetic technical documentation, chunked and embedded for retrieval.</p>
      </div>

      {error && <div className="rounded-lg border border-red/30 bg-red/5 p-4 text-sm text-red">{error}</div>}

      <Card className="p-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
              placeholder="Search the knowledge base, e.g. 'PIM interference troubleshooting'"
              className="w-full rounded-md border border-border bg-surface-2 py-2.5 pl-10 pr-3 text-sm text-text placeholder:text-text-faint focus:border-cyan focus:outline-none"
            />
          </div>
          <button onClick={runSearch} disabled={searching} className="flex items-center gap-2 rounded-md bg-cyan px-4 py-2.5 text-sm font-medium text-bg hover:bg-cyan/90 disabled:opacity-50">
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </button>
        </div>
      </Card>

      {results && (
        <Card>
          <CardHeader title="Search Results" subtitle={`${results.length} passages`} />
          <div className="divide-y divide-border">
            {results.length === 0 ? <EmptyState message="No results." /> : results.map((r) => (
              <div key={r.chunk_id} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text">{r.title} <span className="text-text-faint">· {r.section}</span></span>
                  <span className="font-mono text-xs text-cyan">{r.score.toFixed(3)}</span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-text-dim">{r.text}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title="Documents" subtitle={`${docs.length} documents`} />
        <div className="divide-y divide-border">
          {docs.map((d) => (
            <div key={d.doc_id} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <FileText className="h-4 w-4 text-cyan" />
                <div>
                  <p className="text-sm text-text">{d.title}</p>
                  <p className="text-xs text-text-faint">{d.owner} · v{d.version} · {d.chunk_count} chunks</p>
                </div>
              </div>
              <Badge>{d.category}</Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
