const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Playwright: intai instalarea locala, apoi cea globala.
let chromium;
try { ({ chromium } = require('playwright')); }
catch (e) { ({ chromium } = require('/home/claude/.npm-global/lib/node_modules/playwright')); }

// Toate fisierele (tpl.html, bed.py, logo, zi*.js) stau langa scriptul asta.
const DIR = process.env.EAM_DIR || __dirname;
// Unde ies clipurile. In sandbox-ul Cowork exista /mnt/user-data/outputs; altfel, ./out
const OUT_DIR = process.env.EAM_OUT
  || (fs.existsSync('/mnt/user-data/outputs') ? '/mnt/user-data/outputs' : path.join(DIR, 'out'));
fs.mkdirSync(OUT_DIR, { recursive: true });

const FPS = 30;
const src = process.argv[2];          // ex. zi23.js

// Patul muzical e compus de noi, prin sinteza (bed.py). Nu vine din nicio
// biblioteca, deci nu are amprenta Content ID si nimeni nu-l poate revendica.
const MOOD_FALLBACK = 'bateria';

(async () => {
  const code = fs.readFileSync(`${DIR}/${src}`, 'utf8');
  fs.writeFileSync(`${DIR}/day.js`, code);
  const DAY = new Function(code + '\n;return DAY;')();
  const name = DAY.name;
  const mood = DAY.mood || MOOD_FALLBACK;

  // momentele de taietura dintre scene — muzica se leaga de ele
  const cuts = [];
  let acc = 0;
  DAY.scenes.forEach(s => { cuts.push(+acc.toFixed(3)); acc += s.dur; });
  const T_TOTAL = +acc.toFixed(3);

  const out = `${DIR}/f_${name}`;
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.goto('file://' + DIR + '/tpl.html');
  await page.waitForFunction(() => window.ready !== undefined);
  await page.evaluate(() => window.ready);
  await page.waitForTimeout(600);
  const T = await page.evaluate(() => window.T_END);
  const total = Math.round(T * FPS);

  for (let i = 0; i < total; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    await page.screenshot({ path: `${out}/f${String(i).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 93 });
  }
  await browser.close();
  if (errs.length) { console.error('ERORI JS:', errs.slice(0, 3)); process.exit(1); }

  // 1. patul muzical, generat pe taieturile acestui clip
  const bed = `${DIR}/bed_${name}.wav`;
  execSync(`python3 ${DIR}/bed.py --cuts ${cuts.join(',')} --end ${T_TOTAL} --mood ${mood} --out ${bed}`,
           { stdio: 'pipe' });

  // 2. imagine + pat muzical, masterizat la -16 LUFS (nivelul pe care il asteapta platformele)
  const fadeAt = Math.max(0, T_TOTAL - 1.9);
  const mp4 = `${OUT_DIR}/eam-clip-${name}.mp4`;
  execSync(
    `ffmpeg -y -v error -framerate ${FPS} -i ${out}/f%04d.jpg -i ${bed} ` +
    `-filter_complex "[1:a]atrim=0:${T_TOTAL},asetpts=PTS-STARTPTS,highpass=f=45,` +
    `equalizer=f=3000:t=q:w=1.6:g=2.5,equalizer=f=9000:t=q:w=1.2:g=3,` +
    `afade=t=out:st=${fadeAt.toFixed(2)}:d=1.9,alimiter=limit=0.95,` +
    `loudnorm=I=-16:TP=-1.5:LRA=11[a]" ` +
    `-map 0:v -map "[a]" -c:v libx264 -preset slow -crf 21 -pix_fmt yuv420p -r ${FPS} ` +
    `-c:a aac -b:a 160k -ar 48000 -ac 2 -shortest -movflags +faststart ${mp4}`);

  const kb = Math.round(fs.statSync(mp4).size / 1024);
  console.log(`${name}: ${T.toFixed(1)}s, ${total} cadre, muzica "${mood}", ${kb} KB -> ${mp4}`);
})();
