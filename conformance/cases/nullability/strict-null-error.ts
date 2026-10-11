// null to non-nullable: TS2322
export function f(x: string | null): string {
  return x;
}
