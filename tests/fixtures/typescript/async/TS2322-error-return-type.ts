// Expect: TS2322
export async function f(): Promise<number> { return 'wrong'; }
