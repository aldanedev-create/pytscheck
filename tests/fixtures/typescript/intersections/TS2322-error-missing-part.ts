// Expect: TS2739
type A = { a: number };
type B = { b: string };
export const x: A & B = { a: 1 };
