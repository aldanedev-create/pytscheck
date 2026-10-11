interface A { a: number; }
interface B { b: string; }
export const x: A & B = { a: 1, b: 'x' };
