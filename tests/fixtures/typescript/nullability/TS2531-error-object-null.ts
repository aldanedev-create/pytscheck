// Expect: TS18047, TS2531
export function f(x: string | null): number {
  return x.length;
}
