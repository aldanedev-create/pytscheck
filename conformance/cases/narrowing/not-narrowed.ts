// not narrowed: TS18047
export function f(x: string | null): number {
  return x.length;
}
