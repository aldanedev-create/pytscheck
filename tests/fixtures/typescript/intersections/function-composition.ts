export function compose<A, B, C>(f: (b: B) => C, g: (a: A) => B) {
  return (a: A): C => f(g(a));
}
