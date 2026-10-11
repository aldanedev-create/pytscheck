// Expect: TS2339
namespace N { export const x: number = 1; }
export const y = N.notDefined;
