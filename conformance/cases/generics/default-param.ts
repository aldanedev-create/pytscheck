// default type parameter
export interface Box<T = string> { value: T; }
export const b: Box = { value: 'a' };
