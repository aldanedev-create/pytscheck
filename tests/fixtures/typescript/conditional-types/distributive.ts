export type Boxed<T> = T extends any ? { value: T } : never;
export const b: Boxed<string | number> = { value: 'a' };
