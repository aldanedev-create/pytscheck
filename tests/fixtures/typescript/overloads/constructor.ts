export class Box {
  constructor(x: string);
  constructor(x: number);
  constructor(public x: string | number) {}
}
