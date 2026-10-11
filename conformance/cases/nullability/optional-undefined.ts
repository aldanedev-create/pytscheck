// possibly undefined access: TS18048
export function f(x?: string): number {
  return x.length;
}
