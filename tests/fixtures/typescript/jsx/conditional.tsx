export function F(props: { show: boolean }) {
  return <div>{props.show ? <span>yes</span> : null}</div>;
}
