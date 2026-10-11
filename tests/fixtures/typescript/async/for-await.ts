export async function f(xs: AsyncIterable<number>): Promise<void> {
  for await (const x of xs) { console.log(x); }
}
