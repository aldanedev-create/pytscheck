export type Partial<T> = { [K in keyof T]?: T[K] };
interface U { a: number; }
export const p: Partial<U> = {};
