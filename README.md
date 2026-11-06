# Momentos Podcast: Shorts-ების ქარხანა

ეს რეპო [@Momentos1Podcast](https://www.youtube.com/@momentos1podcast) არხისთვისაა. ერთი ბრძანებით
ესპანურენოვანი პოდკასტის ეპიზოდიდან შერჩეულ მომენტებს ატვირთვისთვის მზა YouTube Shorts-ებად აქცევს:

- 1080×1920, 9:16 ფორმატი
- სუბტიტრები სიტყვა-სიტყვით: ნათქვამი სიტყვა ყვითლად ინთება (Montserrat ფონტი უკვე რეპოშია)
- ზემოთ სათაური, რომელიც მაყურებელს აჩერებს, და წყაროს მითითება (`ROCA PROJECT #114 · Borja Moreno`)
- ჭრა ზუსტად სიტყვის საზღვარზე. ერთ კლიპს რამდენიმე მონაკვეთის შეერთებაც შეუძლია (jump cut)
- ხმის დონე გასწორებულია (−14 LUFS), დასაწყისი და ბოლო რბილადაა გადასული
- ყველა ვიდეოს გვერდით დევს `youtube.txt` ფაილი: სათაური, აღწერა ჰეშთეგებით და დასამაგრებელი კომენტარი

რომელი პოდკასტი და რატომ, ასევე ყველა მომენტის ცხრილი: [`docs/research-2026-11.md`](docs/research-2026-11.md).

## მზა გეგმა: ROCA PROJECT #114 (8 Shorts)

[`clips/roca-project-114.json`](clips/roca-project-114.json) არის ეპიზოდი
[#114 «MÉDICO FORENSE: LA MUERTE HABLA», Borja Moreno](https://www.youtube.com/watch?v=XDDt-IzJOcA).
გამოვიდა 2026-11-04 და 2 დღეში 546 ათასი ნახვა დააგროვა.

| # | ფაილი | ხანგრძლ. | სათაური |
|---|---|---|---|
| 1 | `01-besar-hoy` | ~52 წმ | Médico forense: «Al que tengáis que besar, besarle hoy» 🤍 |
| 2 | `02-planta-cadaver` | ~54 წმ | Del cuerpo de esta mujer creció una planta… |
| 3 | `03-corazon-sigue-latiendo` | ~47 წმ | La asesinaron frente a un colegio… y su corazón sigue latiendo |
| 4 | `04-asesino-perfecto` | ~49 წმ | Médico forense: «Nosotros somos el asesino perfecto» 😳 |
| 5 | `05-ceuta` | ~56 წმ | «No quiero seguir haciendo autopsias a chicos de 20 años» 💔 |
| 6 | `06-la-maldad-no-existe` | ~45 წმ | Médico forense: «Para mí, la maldad no existe» 🤔 |
| 7 | `07-movieron-el-cadaver` | ~45 წმ | El forense supo que habían movido el cadáver solo con mirarlo 🕵️ |
| 8 | `08-manoli-felicidad` | ~55 წმ | Cómo afronta la muerte un médico forense: «Manoli, esta es tu felicidad» |

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
| `blur` (ნაგულისხმევი) | ეპიზოდი შუაშია, უკან იგივე კადრი დაბურული, ზემოთ სათაური, ქვემოთ სუბტიტრები | ყოველთვის გამოდგება, არავის ჭრის |
| `face` | მთელ ეკრანზე, კადრი სახეს მისდევს (OpenCV) | ახლო ხედი, ერთი ადამიანი კადრში |
| `center` | უბრალოდ ცენტრიდან ამოჭრილი | თუ მოსაუბრე ყოველთვის ცენტრშია |

`--zoom 1.3` (`blur` რეჟიმში) ეპიზოდის კადრს ადიდებს და გვერდებს აჭრის.
რეჟიმი და zoom თითო კლიპზე JSON-შიც შეიძლება მიეთითოს (`"reframe": "face"`).

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
  "hook": "Texto grande arriba del vídeo",
  "segments": [
    {"start": "56:32.0", "end": "57:23.6", "start_at": "yo", "end_after": "sea"}
  ],
  "description": "...",
  "pinned_comment": "¿...? Responde SÍ o NO 👇",
  "hashtags": ["#Tema"]
}
```

- `start`/`end`: დრო ეპიზოდში (`MM:SS.s` ან `H:MM:SS.s`)
- `start_at` / `end_after` (არასავალდებულო): კლიპი ზუსტად ამ სიტყვით დაიწყება და დასრულდება
  (სკრიპტი მითითებულ დროსთან ყველაზე ახლოს მყოფ შემთხვევას ირჩევს)
- თუ `segments`-ში რამდენიმე მონაკვეთია, ისინი ერთ კლიპად შეერთდება

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
