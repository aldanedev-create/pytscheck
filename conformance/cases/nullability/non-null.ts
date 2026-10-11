// non-null assertion
export function f(x: string | null): number {
  return x!.length;
}
