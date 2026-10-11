export type Readonly<T> = { readonly [K in keyof T]: T[K] };
interface U { a: number; b: string; }
export const r: Readonly<U> = { a: 1, b: 'x' };
