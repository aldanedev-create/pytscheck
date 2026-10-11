// default parameter value
export function greet(name: string, greeting = 'hi'): string {
  return greeting + ', ' + name;
}
