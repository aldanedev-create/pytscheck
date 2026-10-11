// generic return violation: TS2322
export function id<T>(x: T): T { return 'wrong'; }
