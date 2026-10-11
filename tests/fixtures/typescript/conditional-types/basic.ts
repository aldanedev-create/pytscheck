export type IsString<T> = T extends string ? true : false;
export const a: IsString<'x'> = true;
export const b: IsString<number> = false;
