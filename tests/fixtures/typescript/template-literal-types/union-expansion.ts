export type Event = 'click' | 'hover';
export type Handler = `on${Capitalize<Event>}`;
export const h: Handler = 'onClick';
