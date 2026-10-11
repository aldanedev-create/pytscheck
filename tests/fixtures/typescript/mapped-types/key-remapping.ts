export type Getters<T> = { [K in keyof T as `get${string & K}`]: () => T[K] };
interface U { a: number; }
export const g: Getters<U> = { geta: () => 1 };
