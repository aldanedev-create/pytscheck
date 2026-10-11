// equality narrowing
export function f(x: string | null): string {
  if (x === null) return '';
  return x;
}
