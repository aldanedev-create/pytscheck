// Expect: TS2322
export function identity<T>(x: T): T { return 'wrong'; }
