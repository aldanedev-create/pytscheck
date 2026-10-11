// optional parameter
export function greet(name: string, greeting?: string): string {
  return (greeting ?? 'hi') + ', ' + name;
}
