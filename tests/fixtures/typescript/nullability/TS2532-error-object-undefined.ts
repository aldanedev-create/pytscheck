// Expect: TS18048, TS2532
export function f(x?: string): number {
  return x.length;
}
