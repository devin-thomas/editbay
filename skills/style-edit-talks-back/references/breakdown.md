# Breakdown: eight videos by corbin (@Corbin_Brown), measured 2026-09-27

Source: the eight newest uploads on 2026-09-27 (4:20 to 11:56, 60.6 minutes in all), studied at 720p and deleted after
measurement; only this text was kept. IDs: R7OVwGsAsPQ (make your AI stop yapping), XBv6Xj55r_U (GPT-6 Astra vs
Fable), cEE_jEiI1a8 (50 hours with Grok 4.7), zxwUxjTiRFw (Shopify goes native), LPsnYiL8BgQ (Jev for beginners),
vfjJHbLUcfc (AI app builders), XXDiW6m8Go0 (Cursor Projects), Irrgbirow54 (the AI stack). Tools: reference_report.py
per video, scene detection at 0.07 on four, word-timed auto-captions for speech rate, and the overview sheets
(one frame every 2 s) read for every opening and sampled through middles and endings.

## Measurements

| | value | how |
|---|---|---|
| speech rate | 203-235 wpm overall (mean 218); 180-268 in the first 30 s | caption words / duration |
| hard scene changes | 3.2-13.8 per minute (mean 8) | reference_report, threshold 0.25 |
| visual events (cut, punch-in, word, prop, counter tick) | 30-60 per minute; median gap 0.23-1.12 s | scene > 0.07 on four videos |
| chapters | 4-8 per video when present (5 of 8); intro 26-58 s; chapters 40-120 s | info.json |
| loudness range | 1.9-2.8 LU (mean 2.3) on every video | reference_report |
| cuts on a music grid | no (10/42 within 2 frames on the shortest) | reference_report |
| palette | near-black 45-60 % (dark UIs, canvas), the green backdrop as the recurring accent, skin | reference_report |

## How a video runs (the openings, timed)

- 0.0-1.5 s: a signature card (colour bars, "PLEASE STAND BY", the channel as a public-access station, the video's
  filename). Every video.
- 1.5-15 s (up to 30): a parody world that stages the premise: a news studio with a BREAKING ticker made of his own
  words (Jev), mission control with a mission-elapsed clock at T+50:00:01 for "50 hours" (Grok), a pixel boss fight
  against YAPBOT with objectives and health bars and his lines as game dialogue (yapping), an anime boardroom with
  Japanese speech bubbles and a chalk outline for the framework he calls dead (Shopify), a street of parody
  billboards (app builders), a mafia boardroom (stack). His likeness is composited in; his lines become the world's
  text.
- Then a hard or glitch cut to the plain A-roll: green backdrop, microphone in frame, jump cuts, and the annotation
  layer on top. Screen recordings and a dark whiteboard canvas carry explanations, with his cut-out webcam in a lower
  corner; the canvas punches in hard on the key word.
- Endings are plain (his profile, the product page) with one last gag: an APPLAUSE sign, a "content declaration" form
  whose last box gets ticked late, an aside like "(he cares)".

## What makes it work (principles)

1. The edit is a second character. It speaks only in text, deadpan: short monospace asides in brackets or parentheses
   that doubt, correct, count or confirm what he just said ("[citation needed]", "(sulking)", "(two of them)",
   "[it did not]", "he checked."). Roughly one every 6-10 s in annotated A-roll (sheets). Some name the editor
   outright ("edited by: a computer", "[ the editor complied. ]").
2. Running-gag counters: a boxed monospace counter in a corner increments every time he does the thing (says a
   buzzword, mispronounces a name, costs himself a sponsor). Four of eight videos; it persists for the chapter.
3. Punch words: one to three words in the heaviest condensed type land on the stressed syllable, beside his head,
   usually with an aside underneath; a repeated word stacks and grows (WEIRD / WEIRD / WEIRD).
4. Parody lower thirds whose second line is the joke (credentials, a "product watch" with a status line, "the fit").
5. A parody world for the cold open, 10-30 s, in which his words are the world's text. All eight open with a bit.
6. Density: something new every 1-2 s (30-60 visual events a minute) over speech with every pause removed
   (203-235 wpm). The picture never waits for the voice.
7. Props with a punchline: product icons as physical objects (falling, stacked, a podium "#1 / #1 (also)"), a
   tombstone for a dead idea, outlined label stamps for a word cloud.
8. Loudness is flat (LRA 2.3 LU): the voice carries; effects never compete with a word.

## Signature to leave with the reference

The colour-bars "PLEASE STAND BY" public-access opener; yellow condensed type with his monospace asides on a green
backdrop; the blue-and-yellow lower-third bar and its wording ("human, has opinions"); AI-generated cartoon versions
of the host; the specific counters and running jokes. A new piece takes the grammar (principles 1-8) in its own
brand's type, palette and worlds.
