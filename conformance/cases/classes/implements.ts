// implements interface
export interface Serializable { serialize(): string; }
export class Obj implements Serializable {
  serialize(): string { return ''; }
}
