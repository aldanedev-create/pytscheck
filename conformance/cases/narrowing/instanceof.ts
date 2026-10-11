// instanceof narrowing
export function f(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
