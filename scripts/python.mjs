// Use the selected virtual environment across Windows, macOS, and Linux.
import { existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawn } from 'node:child_process';

const windows = process.platform === 'win32';
const environment = process.env.VIRTUAL_ENV || resolve('.venv');
const virtualPython = join(environment, windows ? 'Scripts/python.exe' : 'bin/python');
const executable = process.env.PYTHON || (existsSync(virtualPython) ? virtualPython : windows ? 'python' : 'python3');
const child = spawn(executable, process.argv.slice(2), { stdio: 'inherit', shell: false });
child.on('error', error => {
  console.error(`Unable to launch Python: ${error.message}. Create .venv or set PYTHON to your interpreter.`);
  process.exitCode = 1;
});
child.on('exit', (code, signal) => { process.exitCode = code ?? (signal ? 1 : 0); });
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
