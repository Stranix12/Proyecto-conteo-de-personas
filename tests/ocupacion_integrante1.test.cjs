const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,
  '../counter/static/counter/app.js'), 'utf8');

for (const [count, capacity, expected, width] of [
  [0, 24, 0, '0%'], [2, 24, 8, '8%'],
  [12, 24, 50, '50%'], [24, 24, 100, '100%'],
  [30, 24, 125, '100%']
]) {
  test(`ocupacion ${count}/${capacity}: ${expected}%`, async () => {
    const elements = new Map();
    const element = id => {
      if (!elements.has(id)) elements.set(id, {
        value: id === 'capacity' ? String(capacity) : '.35',
        style: {}, classList: {toggle() {}},
        addEventListener() {}, replaceChildren(...items) {this.items = items;},
        getContext() {return {drawImage() {}};},
        toBlob(callback) {callback({});}
      });
      return elements.get(id);
    };
    const context = vm.createContext({
      document: {getElementById: element, cookie: '',
        createElement: () => ({}), createTextNode: text => ({textContent: text})},
      window: {addEventListener() {}},
      FormData: class {append() {}},
      fetch: async () => ({ok: true,
        headers: {get: () => 'application/json'},
        json: async () => ({count, sessions: [], boxes: [],
          processing_ms: 10, image: '', over_capacity: count > capacity})})
    });
    vm.runInContext(source, context);
    await vm.runInContext('processFrame({naturalWidth:640,naturalHeight:480})', context);
    assert.equal(element('occupancy').items[0].textContent, expected);
    assert.equal(element('meter').style.width, width);
    assert.equal(element('alert').hidden, count <= capacity);
  });
}
