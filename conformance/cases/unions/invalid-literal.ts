// literal not in union: TS2322
export type T = 'a' | 'b';
export const t: T = 'z';
