import corpus from "./generated/content.json" with { type: "json" };

export type Document = {
  readonly path: string;
  readonly title: string;
  readonly skill: string | null;
  readonly tool: string | null;
  readonly description: string;
  readonly text: string;
  readonly sha256: string;
};

export type SearchHit = {
  readonly path: string;
  readonly title: string;
  readonly score: number;
  readonly offset: number;
  readonly excerpt: string;
};

type IndexedDocument = {
  readonly document: Document;
  readonly heading: string;
  readonly body: string;
};

export const revision: string = corpus.revision;
export const documents: readonly Document[] = corpus.documents;
const index: readonly IndexedDocument[] = documents.map((document: Document): IndexedDocument => ({
  document,
  heading: `${document.path} ${document.title} ${document.description}`.toLowerCase(),
  body: document.text.toLowerCase(),
}));

export function findDocument(path: string): Document | undefined {
  return documents.find((document: Document): boolean => document.path === path);
}

export function documentUri(path: string): string {
  return `editbay://docs/${path}`;
}

export function documentUrl(baseUrl: string, path: string): string {
  return `${baseUrl}/docs/${path.split("/").map(encodeURIComponent).join("/")}`;
}

export function searchDocuments(query: string, limit: number): readonly SearchHit[] {
  const terms: readonly string[] = query.toLowerCase().trim().split(/\s+/).slice(0, 12);
  if (terms.length === 0 || terms[0] === "") throw new Error("Search requires a nonblank query");
  let hits: SearchHit[] = [];
  for (const entry of index) {
    if (!terms.every((term: string): boolean => entry.heading.includes(term) || entry.body.includes(term))) continue;
    const score: number = terms.reduce((total: number, term: string): number => total + (entry.heading.includes(term) ? 10 : 1), 0);
    const match: number = Math.max(0, entry.body.indexOf(terms[0] ?? ""));
    const offset: number = Math.max(0, match - 120);
    hits.push({ path: entry.document.path, title: entry.document.title, score, offset, excerpt: entry.document.text.slice(offset, offset + 600) });
  }
  hits.sort((a: SearchHit, b: SearchHit): number => b.score - a.score || a.path.localeCompare(b.path));
  return hits.slice(0, limit);
}
