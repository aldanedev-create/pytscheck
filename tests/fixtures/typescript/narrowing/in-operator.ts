export function f(o: { a: number } | { b: string }): number {
  if ('a' in o) { return o.a; }
  return o.b.length;
}
