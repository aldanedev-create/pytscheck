export function first<T extends { length: number }>(x: T): number {
  return x.length;
}
