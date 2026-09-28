import { copyFile, mkdir } from 'node:fs/promises';

await mkdir('dist/vendor', { recursive: true });
for (const name of ['index.html', 'main.js', 'config.mjs']) {
  await copyFile(name, `dist/${name}`);
}
for (const name of ['ov-web-rtc.js', 'placeholder.jpg']) {
  await copyFile(`node_modules/@nvidia/ov-web-rtc/dist/${name}`, `dist/vendor/${name}`);
}
await copyFile('node_modules/@nvidia/ov-web-rtc/LICENSE.txt', 'dist/vendor/LICENSE.txt');
await copyFile('node_modules/is-plain-object/LICENSE', 'dist/vendor/is-plain-object.LICENSE');
