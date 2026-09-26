# tools — cum se randează un clip pentru un rând din Calendar Editorial

1. **Scrie datele rândului** într-un `zi<N>.js` lângă scripturi: `var DAY = { mood, name, scenes:[...] }`. `mood` e unul din `bateria` / `costuri` / `incarcare` / `piata` și alege patul muzical după pilonul editorial. Tipuri de scenă: `text`, `big`, `bars`, `duo`, `close`.
2. **Rulează** `node buildday.cjs zi<N>.js`. Playwright randează fiecare cadru la 30 fps din `tpl.html`, `bed.py` compune muzica pe tăieturile scenelor, ffmpeg muxează.
3. **Rezultatul**: `eam-clip-<name>.mp4`, 1080×1920, H.264 + AAC 48 kHz stereo, −16 LUFS, `+faststart`, în `./out` (sau `/mnt/user-data/outputs` dacă există). Un clip de 25–30 s are ~1,3 MB.
4. **Urcă fișierul în rădăcina acestui repo** și pune în Calendar Editorial, la `Link video`: `https://raw.githubusercontent.com/mariusrius4/eam-media/main/eam-clip-<name>.mp4`. Pentru video se folosește `raw.githubusercontent.com`, niciodată jsDelivr — politica lor interzice explicit video.

**Regula copertei.** Prima scenă se randează complet formată din cadrul zero, fără animație de intrare: miniatura din feed nu are voie să fie ecran negru. E implementată în `tpl.html` (`lt = (ci === 0) ? 99 : ...`) — nu o scoate. Din același motiv, nu pune o scenă `big` prima: numărul ar apărea direct la valoarea finală, fără numărătoarea de la zero.

**Muzica e compusă aici, de la zero, prin sinteză** (`bed.py`, numpy). Nu vine din nicio bibliotecă, deci nu are amprentă Content ID și nimeni nu o poate revendica. `bed.py` e dovada de autorship — se păstrează.

**Cerințe:** Node + Playwright (Chromium), Python 3 cu numpy și scipy, ffmpeg, și fonturile Poppins în `/usr/share/fonts/truetype/google-fonts/`. Suprascrie căile cu `EAM_DIR` și `EAM_OUT` dacă rulezi din altă parte.
