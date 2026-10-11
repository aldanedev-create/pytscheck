// wrong argument type: TS2345
export function add(a: number, b: number): number { return a + b; }
add(1, 'two');
