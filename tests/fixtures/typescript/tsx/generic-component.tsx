export function Box<T>(props: { value: T }) {
  return <div>{String(props.value)}</div>;
}
