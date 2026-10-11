export function f(): Promise<number> {
  return Promise.resolve(1).then((x) => x + 1);
}
