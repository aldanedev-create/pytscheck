// structural compatibility
interface A { a: number; }
interface B { a: number; b: string; }
const a: A = { a: 1 };
const b: B = { a: 1, b: 'x' };
const aFromB: A = b;
export { a, b, aFromB };
