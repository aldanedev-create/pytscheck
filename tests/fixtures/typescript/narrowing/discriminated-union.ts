type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'square'; side: number };
export function area(s: Shape): number {
  if (s.kind === 'circle') return Math.PI * s.radius ** 2;
  return s.side ** 2;
}
