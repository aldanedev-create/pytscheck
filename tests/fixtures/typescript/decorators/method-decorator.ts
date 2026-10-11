function log(target: object, key: string, desc: PropertyDescriptor): void {}
export class C { @log method(): void {} }
