export abstract class Shape { abstract area(): number; }
export class Circle extends Shape {
  constructor(private r: number) { super(); }
  area(): number { return Math.PI * this.r ** 2; }
}
