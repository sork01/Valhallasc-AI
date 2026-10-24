const fs = require('node:fs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
requireMemoryLimit();
const relative = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('::')[1];
for (const key of ['memory.max', 'memory.swap.max', 'cpu.max', 'pids.max']) console.log(`${key}=${fs.readFileSync('/sys/fs/cgroup' + relative + '/' + key, 'utf8').trim()}`);
console.log('Resource guard passed; no server or browser was launched.');
