export function f(x: { a: number } | { b: string }): string {
  if ('a' in x) return String(x.a);
  return x.b;
}
