// typeof narrowing
export function f(x: string | number): string {
  if (typeof x === 'string') return x.toUpperCase();
  return String(x);
}
