// benchmark fixture: tiny: single small file, no errors

export const a: number = 1;
export const b: string = 'x';
export const c: boolean = true;
export function add(x: number, y: number): number {
  return x + y;
}
export interface P { x: number; y: number; }
export const p: P = { x: 1, y: 2 };
export type Pair = readonly [number, string];
export const pair: Pair = [1, 'a'] as const;
