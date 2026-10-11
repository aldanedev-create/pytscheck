// basic class with parameter properties
export class Point {
  constructor(public x: number, public y: number) {}
  distance(): number { return Math.hypot(this.x, this.y); }
}
