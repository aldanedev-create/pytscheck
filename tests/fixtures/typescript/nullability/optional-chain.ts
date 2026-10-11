export function f(x: { a?: { b?: number } }): number {
  return x.a?.b ?? 0;
}
