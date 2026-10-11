export function f(x: string): string;
export function f(x: string, y?: number): string;
export function f(x: string, y?: number): string { return x + (y ?? 0); }
