// Expect: TS2322
export type IsString<T> = T extends string ? true : false;
export const a: IsString<'x'> = false;
