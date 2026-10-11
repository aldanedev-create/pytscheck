// Expect: TS2345, TS2344
export function first<T extends { length: number }>(x: T) {}
first(42);
