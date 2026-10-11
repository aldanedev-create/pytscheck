export function List({ items }: { items: string[] }) {
  return <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul>;
}
