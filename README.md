# Momentos Podcast: Shorts-ების ქარხანა

ეს რეპო [@Momentos1Podcast](https://www.youtube.com/@momentos1podcast) არხისთვისაა. ერთი ბრძანებით
ესპანურენოვანი პოდკასტის ეპიზოდიდან შერჩეულ მომენტებს ატვირთვისთვის მზა YouTube Shorts-ებად აქცევს:

- 1080×1920, მთელ ეკრანზე, კადრი მოსაუბრის სახეს მისდევს
- სტილი აღებულია ყველაზე წარმატებული ესპანური პოდკასტ-Shorts-ებიდან ([კვლევა](docs/shorts-style-research.md)):
  - დიდი ორხაზიანი სათაური პირველ 3 წამში, ერთი სიტყვა ყვითლად (Anton ფონტი);
  - სუბტიტრები 1–2 სიტყვით, UPPERCASE, ნათქვამი სიტყვა ყვითლად ინთება (Montserrat Black);
  - «MOMENTOS PODCAST» ეტიკეტი და წყაროს მითითება (`ROCA PROJECT #114 · Borja Moreno`);
  - სურვილისამებრ ფონზე ჩუმი მუსიკა (`--music`)
- ფონტები უკვე რეპოშია, ყველა OFL ლიცენზიით
- ჭრა ზუსტად სიტყვის საზღვარზე. ერთ კლიპს რამდენიმე მონაკვეთის შეერთებაც შეუძლია (jump cut)
- ხმის დონე გასწორებულია (−14 LUFS), დასაწყისი და ბოლო რბილადაა გადასული
- ყველა ვიდეოს გვერდით დევს `youtube.txt` ფაილი: სათაური, აღწერა ჰეშთეგებით და დასამაგრებელი კომენტარი

რომელი პოდკასტი და რატომ, ასევე ყველა მომენტის ცხრილი: [`docs/research-2026-11.md`](docs/research-2026-11.md).

## მზა გეგმა: ROCA PROJECT #114 (8 Shorts)

[`clips/roca-project-114.json`](clips/roca-project-114.json) არის ეპიზოდი
[#114 «MÉDICO FORENSE: LA MUERTE HABLA», Borja Moreno](https://www.youtube.com/watch?v=XDDt-IzJOcA).
გამოვიდა 2026-11-04 და 2 დღეში 546 ათასი ნახვა დააგროვა.

| # | ფაილი | ხანგრძლ. | სათაური | ვიდეოზე (პირველი 3 წმ) |
|---|---|---|---|---|
| 1 | `01-besar-hoy` | ~52 წმ | Un médico forense revela por qué NO quiere que le incineren 🥀 | NO QUIERE QUE LE **INCINEREN** |
| 2 | `02-planta-cadaver` | ~54 წმ | A esta mujer le creció una PLANTA en el cuerpo… y el forense hizo esto 🌱 | LE CRECIÓ UNA **PLANTA** |
| 3 | `03-corazon-sigue-latiendo` | ~47 წმ | La asesinaron frente a un colegio… y su CORAZÓN sigue latiendo 💔 | SU CORAZÓN **SIGUE LATIENDO** |
| 4 | `04-asesino-perfecto` | ~49 წმ | Un médico forense confiesa por qué serían el ASESINO PERFECTO 😳 | EL ASESINO **PERFECTO** |
| 5 | `05-ceuta` | ~56 წმ | Lo más DURO que ha vivido un médico forense en Ceuta 💔 | AUTOPSIAS A **CHICOS DE 20 AÑOS** |
| 6 | `06-la-maldad-no-existe` | ~45 წმ | ¿Existe la MALDAD? Un médico forense responde 🤔 | ¿EXISTE LA **MALDAD**? |
| 7 | `07-movieron-el-cadaver` | ~45 წმ | Movieron el cadáver… y el RIGOR MORTIS los delató 🕵️ | MOVIERON EL **CADÁVER** |
| 8 | `08-manoli-felicidad` | ~55 წმ | Un médico forense revela cómo afronta la MUERTE 🥀 | MANOLI, ESTA ES **TU FELICIDAD** |

ყველა სათაურს ბოლოში `#shorts #podcast` აქვს.

## ინსტალაცია (ერთხელ)

1. **Python 3.10+** და **ffmpeg** (libass-ით, სუბტიტრების ჩასაწვავად):
   - Windows: `winget install Gyan.FFmpeg` (full build)
   - macOS: `brew install ffmpeg` (თუ self-test libass-ზე იჩივლებს: `brew install ffmpeg-full`)
   - Linux: `sudo apt install ffmpeg`
2. ბიბლიოთეკები:
   ```bash
   pip install -r requirements.txt
   ```
3. YouTube-დან ჩამოტვირთვას yt-dlp-ს JavaScript runtime სჭირდება. საუკეთესოა [Deno](https://deno.com)
   (`winget install DenoLand.Deno` / `brew install deno`). Node.js-იც გამოდგება.
4. შემოწმება (ინტერნეტი არ სჭირდება, სატესტო ვიდეოს სამივე რეჟიმში აკეთებს):
   ```bash
   python scripts/make_shorts.py --selftest
   ```

## გაშვება

```bash
# ყველა 8 კლიპი (ეპიზოდი ერთხელ ჩამოიტვირთება work/ საქაღალდეში)
python scripts/make_shorts.py clips/roca-project-114.json

# მხოლოდ კონკრეტული კლიპები
python scripts/make_shorts.py clips/roca-project-114.json --only 01 04

# ჯერ სწრაფი, დაბალი ხარისხის ვერსია (ჭრის შესამოწმებლად)
python scripts/make_shorts.py clips/roca-project-114.json --fast
```

შედეგი იქმნება აქ: `output/roca-project-114/<id>/<id>.mp4` + `youtube.txt`.
ყველა ტექსტი ერთად: `output/roca-project-114/UPLOAD_SHEET.md`.

### კადრის რეჟიმები (`--reframe`)

| რეჟიმი | როგორ გამოიყურება | როდის |
|---|---|---|
| `face` (ნაგულისხმევი) | მთელ ეკრანზე, კადრი სახეს მისდევს (OpenCV). სახე თუ ვერ იპოვა, ცენტრიდან ჭრის | ყველა წარმატებული Short ასეა |
| `center` | უბრალოდ ცენტრიდან ამოჭრილი | თუ მოსაუბრე ყოველთვის ცენტრშია |
| `blur` | ეპიზოდი შუაშია, უკან იგივე კადრი დაბურული | ფართო კადრი, სადაც ორივე ადამიანი უნდა ჩანდეს |

`--zoom 1.3` (`blur` რეჟიმში) ეპიზოდის კადრს ადიდებს და გვერდებს აჭრის.
რეჟიმი და zoom თითო კლიპზე JSON-შიც შეიძლება მიეთითოს (`"reframe": "face"`).

### ფონური მუსიკა

```bash
python scripts/make_shorts.py clips/roca-project-114.json --music musica/triste.mp3 --music-volume 0.10
```

მუსიკა ხმის ქვეშ ძალიან ჩუმად ერთვება და ბოლოს რბილად ქრება. გამოიყენე მხოლოდ ისეთი ტრეკი, რომლის გამოყენების უფლებაც გაქვს
(მაგ., YouTube Audio Library). ალტერნატივა: ატვირთვისას YouTube-ის რედაქტორში მუსიკა თავად დაამატე.

### სუბტიტრები

ნაგულისხმევად YouTube-ის ესპანური ავტო-სუბტიტრები გამოიყენება, რადგან მათში თითოეული სიტყვის დროა მითითებული.
უფრო ზუსტი ტექსტისთვის (სწორი სასვენი ნიშნები, სახელები):

```bash
pip install faster-whisper
python scripts/make_shorts.py clips/roca-project-114.json --whisper          # small მოდელი
python scripts/make_shorts.py clips/roca-project-114.json --whisper medium   # უფრო ზუსტი, უფრო ნელი
```

ყოველ კლიპს გვერდით `<id>.ass` ფაილი უდევს. სუბტიტრებში შეცდომა თუ შეგხვდა, ეს ფაილი ნებისმიერ
ტექსტურ რედაქტორში გაასწორე და იმავე კლიპის რენდერი `--keep-subs`-ით გაიმეორე:

```bash
python scripts/make_shorts.py clips/roca-project-114.json --only 03 --keep-subs
```

თუ სუბტიტრებს CapCut-ში ამატებ, გამოიყენე `--no-captions`.

## ახალი ეპიზოდის დამატება

დააკოპირე `clips/roca-project-114.json` და შეცვალე `source.url`, `credit`, `description_footer` და კლიპები:

```json
{
  "id": "01-mi-clip",
  "title": "Título para YouTube #shorts",
  "hook": "TEXTO GRANDE | CON *PALABRA* EN AMARILLO",
  "segments": [
    {"start": "56:32.0", "end": "57:23.6", "start_at": "yo", "end_after": "sea"}
  ],
  "description": "...",
  "pinned_comment": "¿...? Responde SÍ o NO 👇",
  "hashtags": ["#Tema"]
}
```

- `hook`: დიდი სათაური პირველ 3 წამში. `|` ნიშნავს ახალ ხაზს, `*…*` კი ყვითელ სიტყვას
- `start`/`end`: დრო ეპიზოდში (`MM:SS.s` ან `H:MM:SS.s`)
- `start_at` / `end_after` (არასავალდებულო): კლიპი ზუსტად ამ სიტყვით დაიწყება და დასრულდება
  (სკრიპტი მითითებულ დროსთან ყველაზე ახლოს მყოფ შემთხვევას ირჩევს)
- თუ `segments`-ში რამდენიმე მონაკვეთია, ისინი ერთ კლიპად შეერთდება
- გეგმის დონეზე: `brand` (ეტიკეტი), `credit`, `reframe`, `music` და `style` (ფერი `highlight`, `caption_size`,
  `caption_max_words`, `headline_size`, `headline_seconds`)

სათაურის, აღწერისა და მონტაჟის წესები: [`docs/shorts-style-research.md`](docs/shorts-style-research.md)

მომენტების მოსაძებნად ტრანსკრიპტი შეგიძლია მე გამომიგზავნო, ან უბრალოდ ეპიზოდის ბმული მომწერო და ახალ გეგმას მე მოვამზადებ.

## პრობლემები

- **«Sign in to confirm you're not a bot»**: ჩამოტვირთვას ბრაუზერის cookies დაამატე:
  `--ytdlp-arg=--cookies-from-browser --ytdlp-arg=chrome`
- **ffmpeg was built without libass**: დააყენე full build (იხ. ინსტალაცია)
- **ეპიზოდი უკვე გადმოწერილი გაქვს**: `--source episodio.mp4 --subs episodio.es.json3`
  (subs-ის გარეშეც მუშაობს `--whisper`-ით)

## უფლებები

არხის აღწერაში წერია, რომ კლიპები ავტორების ნებართვით ქვეყნდება. ატვირთვამდე ROCA PROJECT-ისგან წერილობითი თანხმობა აიღე
(კონტაქტი ეპიზოდის აღწერიდან: info@rocaproject.com). ROCA PROJECT-ს საკუთარი clips არხიც აქვს, ამიტომ ნებართვის გარეშე
ატვირთულ კლიპებს Content ID-ის claim შეიძლება მოხვდეს.
