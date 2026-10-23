'use strict';
// Older Safari (iOS before 15.4) lacks these; the sprite loader and several dialogs call them, so define them first.
if (!Object.hasOwn) Object.defineProperty(Object, 'hasOwn', { value: (object, key) => Object.prototype.hasOwnProperty.call(object, key), configurable: true, writable: true });
for (const type of [Array, String]) if (!type.prototype.at) Object.defineProperty(type.prototype, 'at', {
  value(index) { index = Math.trunc(index) || 0; if (index < 0) index += this.length; return index < 0 || index >= this.length ? undefined : this[index]; },
  configurable: true, writable: true,
});
