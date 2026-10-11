// Expect: TS2540
export type Readonly<T> = { readonly [K in keyof T]: T[K] };
interface U { a: number; }
export const r: Readonly<U> = { a: 1 };
r.a = 2;
