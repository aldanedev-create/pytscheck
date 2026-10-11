export type ElementType<T> = T extends (infer U)[] ? U : never;
export const e: ElementType<number[]> = 1;
