// Expect: TS2322
export type Greeting = `hello ${string}`;
export const g: Greeting = 'goodbye';
