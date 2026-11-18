# Dictionary OCR pilots: Kittel 1894 and Ziegler 1876

I ran `kan_ft_ofl3` (release v0.2.0) and Tesseract's stock `kan` model over 20 pages of each of 2 public-domain dictionaries to decide whether a full digitization is worth doing:

- F. Kittel, *A Kannada-English Dictionary*, Basel Mission Book & Tract Depository, Mangalore, 1894. Kannada to English, l + 1752 pages.
- F. Ziegler, *A School-Dictionary, English and Canarese*, first edition, Basel Mission Book & Tract Depository, Mangalore, 1876. English to Kannada, about 565 pages.

Only the 1894 Kittel is used here. The University of Madras revision (1968 to 1971, ed. M. Mariappa Bhat) is in copyright, so DSAL's Kittel and the archive.org uploads of the 4-volume Madras edition were not downloaded or used. I checked the title page of every scan below.

**Result.** Ziegler is worth a full run: with the page cut into columns first, `kan_ft_ofl3+eng` reads its Kannada glosses at 7.6% CER (10.4% akshara error rate), and the whole book takes about 26 minutes with 2 Tesseract processes on an Apple Silicon Mac. The English headwords need work, since Tesseract's English model drops Ziegler's pronunciation marks. Kittel is not ready: Kannada CER is 22.7% at best and only 65% of Kannada headwords come out exactly, so a full run now would give a rough search index, not a text. The numbers rest on 60 lines per book that I transcribed by reading the scans; a Kannada reader should check them.

## Sources

| Book | Host and link | Edition on the title page | Images | Resolution and format | Quality | Rights stated by the host |
|---|---|---|---|---|---|---|
| Kittel | Tübingen UB, Ci XIV 80 a, [opendigi](https://opendigi.ub.uni-tuebingen.de/opendigi/CiXIV80a) | 1894, Mangalore | 1813 | not reached: the server did not answer from my network on 2026-11-18 | | |
| Kittel | Same Tübingen scan, mirrored on archive.org as [dli.CiXIV80a](https://archive.org/details/dli.CiXIV80a), raw image zip | 1894, Mangalore | 1813 | color JPEG, 3057 x 4392 px, 2.1 MB a page | Even light, no thresholding, sharp; some show-through; pages near the front curve into the spine | Tübingen IIIF manifest in the mirror: CC BY-SA 3.0. Deutsche Digitale Bibliothek lists the Tübingen Kittel as Public Domain Mark 1.0 |
| Kittel | Google Books SeQ2AQAAMAAJ (University of Minnesota copy), on archive.org as [kittel-a-kannada-english-dictionary](https://archive.org/details/kittel-a-kannada-english-dictionary) and [KittelKannadaEnglishDictionary](https://archive.org/details/KittelKannadaEnglishDictionary) | 1894, Mangalore | 1818 and 1833 | grayscale JP2 from a near-bitonal Google scan, about 4129 x 5959 px (300 ppi in the second copy) | Thresholded: thin strokes break and the counters of Kannada letters fill in | Uploaders marked both Public Domain Mark 1.0. Google asks that its scan files be used for non-commercial purposes |
| Kittel | CIIL Bharatavani copy, archive.org [dli.language.1683](https://archive.org/details/dli.language.1683) (same PDF as 3 other uploads) | 1894, Mangalore, with a new cover | 1803 | 4200 x 5552 px, 600 ppi | The Google/Minnesota scan again (same bookseller stamp), upscaled | CC BY-NC 4.0 in the item metadata |
| Kittel | Central Secretariat Library, New Delhi, archive.org [dli.csl.8728](https://archive.org/details/dli.csl.8728) | 1894, Mangalore | 1802 | 3756 x 5600 px, 600 ppi | Yellowed paper, faded print, strong show-through | none stated |
| Kittel | HathiTrust | | | | Not checked: the catalog and page server answer scripted clients with a browser challenge | |
| Ziegler | Tübingen UB, Ci XIV 97, [opendigi](https://opendigi.ub.uni-tuebingen.de/opendigi/CiXIV97) | 1876, Mangalore | 585 | not reached, as above | | |
| Ziegler | Same Tübingen scan, mirrored on archive.org as [dli.CiXIV97](https://archive.org/details/dli.CiXIV97), raw image zip | 1876, Mangalore | 585 | color JPEG, 2251 x 3539 px, 1.2 MB a page | Foxing, show-through, and the edge of the facing page in the frames I checked | Tübingen METS in the mirror: CC BY-SA 3.0. The library's current label for its other Ziegler editions is "copyright not evaluated" |
| Ziegler | Google Books 13EIAAAAQAAJ, on archive.org as [ziegler-a-school-dictionary-english-and-canarese](https://archive.org/details/ziegler-a-school-dictionary-english-and-canarese) | 1876, Mangalore | 585 | grayscale JP2 from a near-bitonal Google scan, about 3019 x 4876 px, 1.2 MB a page | Cropped to the page, deskewed, clean; fine marks (dots below letters, primes) are sometimes lost | Uploader marked it Public Domain Mark 1.0. Google asks that its scan files be used for non-commercial purposes |

Later Ziegler editions exist (1889, 1896, 1929) and were not used.

**Public-domain basis.** Kittel's dictionary was published in 1894 and Ferdinand Kittel died in 1903. Ziegler's was published in 1876 and Friedrich Ziegler died on 18 November 1906 ([Who was who in Indology](https://whowaswho-indology.info/?p=4544)). Both authors died more than 100 years ago, so both works are out of copyright in India (life plus 60 years), the EU (life plus 70) and the US (published before 1931). The hosts attach their own terms to the image files (CC BY-SA 3.0 for the Tübingen scans). This pilot does not redistribute any image: it commits only URLs, checksums, OCR text and transcriptions, and it credits each scan's library. A request to Tübingen for permission to use its scans is in preparation. I am not a lawyer; this is the basis I relied on.

**Chosen scans.** For Kittel, the Tübingen scan: it is the only one in continuous tone, and the Google scan's thresholding damages Kannada letters (the second table below measures this). For Ziegler, the Google scan: it is cropped and clean, column cutting works on it, and it gave the lowest Kannada CER. The 2 scans score within the sample's noise, and the Tübingen color scan shows the fine pronunciation marks more clearly, so it is the better copy to proofread against. Every scan was fetched from archive.org, since the Tübingen server could not be reached.

## Method

**Pages.** 20 content pages per book, evenly spaced from the first to the last page of the dictionary so they cover the alphabet: Kittel pages 10, 101, 193, ... 1745, Ziegler pages 14, 43, 71, ... 559, plus each title page. `pages.tsv` lists every image URL and its SHA-256. `fetch.py` downloads them through the repository's HTTP client (robots.txt, 1 request per second, request log) and checks the hashes. The images are not committed.

**OCR.** Tesseract 5.5.4 with LSTM only (`--oem 1`), 1 thread per process, 2 processes at a time, on an Apple Silicon Mac. `kan` is the stock tessdata_best model; `eng` is the tessdata_fast model that Homebrew installs. Configurations:

- `kanft+eng`, `kanft` and `kan+eng`, each with page segmentation mode 3 (automatic, finds columns) and 4 (a single column of text);
- `cols`: the page is first cut into its 2 columns by `kannada_ocr.columns` (printed area grown from the page center, gutter at the emptiest vertical band, vertical rules ignored), then each column is read with mode 4 or 6.

`ocr.py` runs them and records wall-clock seconds per page.

**Reference.** From each page I took 3 lines with `sample.py`: an entry in the upper left column, an entry in the middle of the right column, and a line low in alternating columns. That gives 60 lines per book: 40 Kittel lines and 48 Ziegler lines start an entry. 2 Ziegler picks fell on a blank strip and a rule, so I replaced them by hand with the next line in the column. I transcribed each line from the image at 2 to 4 times magnification, character by character, as printed: Kittel's transliteration with its diacritics (č, š, ṭ, ḍ, ṇ, ḷ, r̤, l̤, ĕ, â), Ziegler's pronunciation marks (macrons, breves, a̤, s̱, ġ, the stress prime as U+2032) and his barred C for a hard c (Ꞓ, ꞓ, U+A792 and U+A793). The `uncertain` column marks every character I could not read with confidence: 17 Kittel lines and 9 Ziegler lines. **I am not a native Kannada reader, and the references were made by reading the scan. They need a check by a Kannada reader before anyone relies on these numbers.** The Kannada CER on lines without any uncertain character is reported as well.

**Scoring.** `score.py` matches each reference line to the stretch of that page's OCR output with the least edit distance (`kannada_ocr.linematch`), then scores with the repository's scorer (`kocr-text`, kannadi normalization). Scores are micro averages over the 60 lines:

- Kannada CER and akshara error rate (AER): only the Kannada-script words of the reference and of the matched stretch;
- Latin CER: only the Latin-letter words, diacritics included, stress primes ignored;
- All CER: the whole line, punctuation and digits included;
- Headword exact: the share of sampled entries whose headword appears exactly in the OCR (Kittel: the Kannada word and its transliteration; Ziegler: the English headword with its marks);
- Headword letters: the same with Latin diacritics, stress primes, syllable hyphens and the bar on C removed from both sides;
- Kannada headword: Kittel only, the Kannada word of the headword exactly.

## Results

All rates are percentages over the 60 sampled lines of each book; lower is better for error rates, higher for headwords. Kittel has 831 Kannada and 1342 Latin reference characters, Ziegler 833 and 617, so 1 point of Kannada CER is about 8 characters. `results/scores.md` has every run.

### Kittel 1894, Tübingen scan (chosen)

| Configuration | Kannada CER | Kannada AER | Kannada CER, lines without uncertain characters | Latin CER | All CER | Headword exact | Headword letters | Kannada headword | Seconds per page |
|---|---|---|---|---|---|---|---|---|---|
| `kanft+eng-psm3` | 22.7 | 24.6 | 23.4 | 15.2 | 15.7 | 7.5 | 37.5 | 65.0 | 12.8 |
| `kanft+eng-psm4` | 26.4 | 30.2 | 27.7 | 17.1 | 17.5 | 5.0 | 27.5 | 55.0 | 13.5 |
| `kanft-psm3` | 49.1 | 75.2 | 51.0 | 100.0 | 49.5 | 0.0 | 0.0 | 62.5 | 10.0 |
| `kanft-psm4` | 49.1 | 74.1 | 50.5 | 100.0 | 50.9 | 0.0 | 0.0 | 52.5 | 10.7 |
| `kan+eng-psm3` | 30.1 | 34.3 | 32.9 | 16.4 | 17.9 | 7.5 | 32.5 | 52.5 | 11.4 |
| `kan+eng-psm4` | 33.5 | 40.3 | 37.2 | 17.8 | 18.6 | 5.0 | 22.5 | 52.5 | 12.0 |
| `kanft+eng-cols-psm4` | 30.1 | 34.1 | 26.5 | 17.7 | 16.6 | 7.5 | 37.5 | 52.5 | 13.9 |
| `kanft+eng-cols-psm6` | 27.0 | 30.6 | 23.4 | 16.2 | 16.1 | 10.0 | 37.5 | 62.5 | 13.6 |
| `kan+eng-cols-psm4` | 30.7 | 37.3 | 30.8 | 16.0 | 16.3 | 10.0 | 37.5 | 55.0 | 12.4 |

### Kittel 1894, Google scan

| Configuration | Kannada CER | Kannada AER | Kannada CER, lines without uncertain characters | Latin CER | All CER | Headword exact | Headword letters | Kannada headword | Seconds per page |
|---|---|---|---|---|---|---|---|---|---|
| `kanft+eng-psm3` | 25.8 | 28.7 | 25.2 | 17.7 | 16.9 | 7.5 | 32.5 | 55.0 | 12.8 |
| `kan+eng-psm3` | 28.5 | 35.5 | 29.3 | 18.1 | 16.0 | 10.0 | 27.5 | 62.5 | 11.4 |

### Ziegler 1876, Google scan (chosen)

| Configuration | Kannada CER | Kannada AER | Kannada CER, lines without uncertain characters | Latin CER | All CER | Headword exact | Headword letters | Seconds per page |
|---|---|---|---|---|---|---|---|---|
| `kanft+eng-psm3` | 11.0 | 14.0 | 11.2 | 35.3 | 18.7 | 8.3 | 43.8 | 5.3 |
| `kanft+eng-psm4` | 11.0 | 13.8 | 11.5 | 35.5 | 17.5 | 6.2 | 41.7 | 5.2 |
| `kanft-psm3` | 21.6 | 34.1 | 22.1 | 100.0 | 37.6 | 0.0 | 0.0 | 4.2 |
| `kanft-psm4` | 18.4 | 30.2 | 18.9 | 100.0 | 36.0 | 0.0 | 0.0 | 3.8 |
| `kan+eng-psm3` | 13.1 | 17.3 | 12.6 | 41.2 | 20.2 | 8.3 | 37.5 | 4.8 |
| `kan+eng-psm4` | 15.6 | 19.9 | 13.8 | 41.6 | 20.7 | 6.2 | 43.8 | 4.8 |
| `kanft+eng-cols-psm4` | 8.8 | 10.8 | 9.3 | 35.5 | 18.1 | 6.2 | 39.6 | 5.5 |
| `kanft+eng-cols-psm6` | 7.6 | 10.4 | 8.3 | 38.2 | 17.4 | 6.2 | 33.3 | 5.5 |
| `kan+eng-cols-psm4` | 12.4 | 16.6 | 13.5 | 37.4 | 19.5 | 6.2 | 39.6 | 5.1 |

### Ziegler 1876, Tübingen scan

| Configuration | Kannada CER | Kannada AER | Kannada CER, lines without uncertain characters | Latin CER | All CER | Headword exact | Headword letters | Seconds per page |
|---|---|---|---|---|---|---|---|---|
| `kanft+eng-psm3` | 13.7 | 16.6 | 14.6 | 35.3 | 19.7 | 4.2 | 31.2 | 5.6 |
| `kanft+eng-psm4` | 9.7 | 12.1 | 8.2 | 35.0 | 18.3 | 6.2 | 37.5 | 5.8 |
| `kanft-psm3` | 19.6 | 30.7 | 19.5 | 100.0 | 37.7 | 0.0 | 0.0 | 4.1 |
| `kanft-psm4` | 19.1 | 29.8 | 18.6 | 100.0 | 36.7 | 0.0 | 0.0 | 4.0 |
| `kan+eng-psm3` | 13.5 | 16.6 | 12.5 | 32.6 | 17.4 | 6.2 | 39.6 | 5.1 |
| `kan+eng-psm4` | 12.5 | 16.6 | 12.9 | 40.5 | 19.3 | 6.2 | 37.5 | 5.4 |
| `kanft+eng-cols-psm4` | 14.5 | 16.9 | 16.1 | 39.9 | 21.9 | 6.2 | 35.4 | 6.2 |
| `kanft+eng-cols-psm6` | 14.8 | 16.4 | 16.3 | 41.6 | 21.3 | 6.2 | 41.7 | 6.3 |
| `kan+eng-cols-psm4` | 12.4 | 17.1 | 12.5 | 34.7 | 17.2 | 6.2 | 43.8 | 5.8 |

What the numbers say:

- `kan_ft_ofl3` beats the stock model on Kannada in both books: Kittel 22.7% against 30.1% CER (mode 3), Ziegler 7.6% against 12.4% (2 columns cut first). Read alone, it turns every English word into Kannada letters (Latin CER 100%), so it needs `+eng`.
- Kittel's Kannada is hard for the model. The errors gather on letters and spellings that modern print no longer uses (ಱ, ೞ, ನ್ದ and ಮ್ಬ where modern print has ಂದ and ಂಬ), on short Kannada words inside English text, and on headwords at the start of a line, which are sometimes dropped. The Kannada digit ೬ appears 93 times in the Kittel output, though the book prints Arabic digits; these are misread marks, likely `=`.
- Latin text loses its marks. Tesseract's `eng` has none of ā, â, ĕ, ṭ, ḍ, ṇ, š, č, r̤ or Ꞓ in its character set, so nearly every headword with a mark comes out wrong: 7.5% (Kittel) and 6.2% to 8.3% (Ziegler) of headwords are exact, against 37.5% and up to 43.8% once marks are removed from both sides. Ziegler's barred C comes out as € (38 times in the chosen run) or is dropped. Over all Latin text, removing the marks lowers Latin CER from 15.2% to 10.7% (Kittel) and from 38.2% to 31.4% (Ziegler), so the marks are about a third of the Latin errors. Much of the rest in Ziegler is short italic labels: in the chosen run `s.`, `a.`, `v. a.` and `v. n.` come out as `8.` 23 times and as Kannada digits (೮., ೫., ೪., ೯.) 49 times, against 341 correct `s.`. Dropped syllable hyphens and dropped line-initial headwords make up most of what is left.
- Cutting the page into columns first helps on clean frames (Ziegler Google: 11.0% to 7.6% Kannada CER) and hurts when the frame holds the edge of the facing page (Ziegler Tübingen: 9.7% to 14.8%). On Kittel, Tesseract's own mode 3 does better than my column cut (22.7% against 27.0%).
- The scans: the Google Kittel scan is 3 points worse on Kannada than Tübingen's (25.8% against 22.7%, same configuration). For Ziegler the 2 scans are within the sample's noise (best Kannada CER 7.6% Google, 9.7% Tübingen; best All CER 17.4% and 17.2%).
- Lines without uncertain characters score about the same as all lines, so my doubtful readings do not drive the totals.

## Full-run estimate

From the chosen configurations (Kittel: Tübingen scan, `kanft+eng-psm3`; Ziegler: Google scan, `kanft+eng-cols-psm6`). Characters per page come from the sample: about 115 lines of 48 characters on a Kittel page and 70 lines of 29 on a Ziegler page, counted on 4 pages of each.

| | Kittel 1894 | Ziegler 1876 |
|---|---|---|
| Pages | 1752 (plus l front matter) | about 565 |
| Seconds per page, 1 Tesseract process | 12.8 | 5.5 |
| OCR time on an Apple Silicon Mac | 6.2 process-hours, about 3.1 hours with 2 processes | 0.9 process-hours, about 26 minutes with 2 processes |
| Disk for the images | 3.8 GB (Tübingen originals, 2.1 MB a page) | 0.7 GB (Google JP2, 1.2 MB a page) |
| Characters per page, estimated | 5,560 (1,590 Kannada, 2,570 Latin) | 2,050 (970 Kannada, 720 Latin) |
| Character errors per page (All CER) | about 870 | about 360 |
| of which in Kannada words | about 360 | about 74 |
| Errors in the whole book | about 1.5 million | about 200,000 |

Correction effort depends on the proofreader, which I did not measure. At an assumed 10 seconds per error, checked against the image, Kittel would take about 4,200 hours and Ziegler about 560 hours; Ziegler's Kannada alone about 115 hours. At Kittel's error rate, retyping would cost about as much as correcting, so Kittel needs a better model first. OCR text for both books is under 20 MB.

## What would improve accuracy most

1. **A Latin model that knows the marks and the italic labels.** Headword accuracy rises from under 10% to about 40% once marks are ignored, and the marks are about a third of all Latin errors. Fine-tuning a Latin model on lines rendered with ā, ĕ, ŏ, ṭ, ḍ, ṇ, ṛ, š, č, r̤, l̤, s̱, ġ and Ꞓ, and with Ziegler's italic `s.`, `a.`, `v. a.`, `v. n.` beside Kannada, starting from Tesseract's `script/Latin`, would help both books, Kittel's transliterations most. Mapping € back to Ꞓ in Ziegler output is a quick first step.
2. **A fine-tune on dictionary pages.** Kittel's Kannada errors sit on old letters and spellings (ಱ, ೞ, ನ್ದ, ಮ್ಬ), on small Kannada type inside English text and on line-initial headwords. A few thousand corrected Kittel lines, which a first OCR pass plus a proofreader can produce, would teach the model this type. Ziegler's Kannada is close to modern print and gains less.
3. **Layout splitting after page cropping.** Cutting columns helped where the frame held only the page and hurt where it held the facing page. Cropping each frame to its page and deskewing it first, then cutting columns and then entries by their hanging indent, would also give each headword its own line for a word-list check (English headwords against an English word list, Kannada headwords against Alar).

## Limits

- The references were made by reading the scan, by someone who is not a native Kannada reader. They need a Kannada reader's check.
- 60 lines per book is a small sample. A difference of a few points between configurations is within its noise.
- Matching a reference line to the closest stretch of OCR output can only flatter the OCR: if the OCR lost a line, the match may land on a similar neighbor (Ziegler's "Anticipation" landed on "Anticipate", which has the same gloss).
- Seconds per page were measured with 2 Tesseract processes running at a time on a shared machine; they are wall-clock times for 1 process.
- Tübingen's own server was unreachable, so its current download terms could not be read. The rights statements above come from the mirrored metadata and from the Deutsche Digitale Bibliothek.

## Files

| File | What it is |
|---|---|
| `pages.tsv` | Every pilot image: book, scan, printed page, URL, SHA-256 |
| `requests.jsonl` | The request log of the download: 1 robots.txt and 84 images |
| `fetch.py` | Downloads the images in `pages.tsv` and checks their hashes |
| `ocr.py` | Runs each configuration and writes `outputs/` |
| `sample.py` | Picks the reference lines and cuts them out for transcribing |
| `score.py` | Scores `outputs/` against `transcriptions/` into `results/` |
| `transcriptions/*.tsv` | The hand transcriptions: page, column, line index, box in the sampled scan (Google for Ziegler), headword, text, uncertain characters |
| `outputs/<book>/<scan>/<config>/<page>.txt` | Tesseract output for every pilot page |
| `outputs/timings.tsv` | Seconds per page for every run |
| `results/scores.json`, `results/scores.md` | All scores |

To reproduce, from the repository root:

```sh
cargo build --release && uv sync
uv run python pilots/dictionaries/fetch.py
mkdir -p data/tessdata   # kan (tessdata_best), eng and kan_ft_ofl3 traineddata
uv run python pilots/dictionaries/ocr.py --tessdata data/tessdata
uv run python pilots/dictionaries/score.py
```

The transcriptions, outputs and this README are CC BY 4.0; the code is MIT OR Apache-2.0.
