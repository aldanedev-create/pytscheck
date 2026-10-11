async function get(): Promise<number> { return 1; }
export async function main(): Promise<void> {
  const n = await get();
  console.log(n);
}
