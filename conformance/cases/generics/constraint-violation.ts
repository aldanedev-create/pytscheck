// constraint violation: TS2345
export function first<T extends { length: number }>(x: T) {}
first(42);
