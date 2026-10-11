// discriminated union narrowing
type S = { k: 'a'; v: number } | { k: 'b'; v: string };
export function f(s: S): string {
  if (s.k === 'a') return String(s.v);
  return s.v;
}
