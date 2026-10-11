export function f(x: string | null): number {
  if (x === null) return 0;
  return x.length;
}
