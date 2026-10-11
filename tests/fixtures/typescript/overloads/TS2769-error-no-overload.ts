// Expect: TS2769
export function f(x: string): string;
export function f(x: string): string { return x; }
f(42);
