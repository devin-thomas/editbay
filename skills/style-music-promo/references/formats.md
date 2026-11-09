# Formats

Lengths assume ~120-130 BPM in 4/4 (a bar ≈ 1.9 s). Scale by the song: plan in bars, then `seconds = bars × 4 × 60 / BPM`.
"Hook" is the section where the drums/bass come in (the map's first full section); "phrase" is 8 bars unless the map
says otherwise. Every format ends on the lockup, and 9:16 versions keep the same bar map.

| format | length | bar map | needs |
|---|---|---|---|
| trailer | 30-45 s | pre-roll ≤ 1.5 s · intro phrase (8) · hook phrase (8) · plain fade into the stop, silent lockup (2) · studio ident (1.5) | product takes, glass plates (intro + lockup), catalog art, stats |
| sizzle reel | 15-30 s | hit on bar 1 of the hook · montage on downbeats and claps (6) · flurry (1) · lockup (1) | product/footage selects, one motif |
| intro / opener | 4-8 s | motif reveal (1-2) · lockup on the last downbeat (1-2); the song keeps going under the content | glass plate or motif, title |
| outro | 8-15 s | fade into the section's last event · lockup (2) · studio ident + end-screen space (≥ 5 s) | lockup plate, links/end-screen zones |
| interstitial / bumper | 1-3 s | one whip or flash into a label on a downbeat, or a half-bar sting | one sound, one word |
| ident / logo sting | 2 bars + a 2-4 s fade or held silence (5.5-8 s; 7.3 s at 140 BPM) | reveal on the last bar before the hook (1) · the hit on the hook's first downbeat, stop at that bar's end (1) · echo tail: wordmark on `hits[1]` | glass plate, or the flat mark (no GPU) |

## Trailer (the worked example, 125 BPM)

| bars | T (s) | role | on screen |
|---|---|---|---|
| pre-roll | 0.00-1.44 | press play | macro on the song row; the real tap at 0.955; waveform waiting |
| 1-2 | 1.50-5.34 | the song starts | pull back to the phone, Now Playing; cut on bar 2; home screen; push into the icon |
| 3-8 | 5.34-16.86 | motif | liquid-glass icon: clear, then filling from bar 5, cover ring from bar 6, spin on bar 7, dive into the liquid on the last beat |
| 9-10 | 16.86-20.70 | drop | flash; product flinging through the catalog; cover wall pulsing on 808s; stat slams on claps |
| 11-14 | 20.70-28.38 | the product | real taps on downbeats/claps; the iPad; the lyric-cued device swap |
| 15 | 28.38-30.30 | flurry | six feature cards on beats then half beats; spectrum ring |
| 16 | 30.30-32.22 | back to the start | the second lyric swap; push in on the pause control |
| 17-18 | 32.22-36.06 | stop + resolve | fade from 31.48 to zero at the real pause (beat 65); silent lockup, type on the grid |
| 19 | 36.06-39.50 | studio | ident on the bar where the verse would have dropped; held to the last frame |

## Picking the window

- The intro phrase is usually quiet (no drums): give it the motif and the product's first action.
- Cut the piece where a section ends: the map's section boundaries are the cut points and the fade points. A bass/drum
  drop-out right after the hook is the natural stop (the "second sixteen").
- If the lyric in the hook names the product's idea (the phone, the drive, the night), anchor a transformation to it.
- For idents and intros from a longer song: reveal on the last bar before the hook; the hit is the hook's first
  downbeat (track_map's first bass/drums entrance, "bass enters at beat 32"); stop at the end of that
  bar, before the next vocal, with a plain fade into the stop (`echo_tail.py --fade-from F --stop S`), then 2-4 s of
  silence or the studio ident's own hit. DemoIdent (cold-read test, made before the owner's ruling, so it used the
  echo throw): bar 8 reveal (T 0.25), bar 9 hit (T 1.964, the 808 enters), stop T 3.627 (51 ms before bar 10's
  vocal), "Demo Artist" at T 4.324, last frame 7.3 s.
- Prefer vocal-free bars for idents and interstitials; the DemoIdent intro's first line (song 9.5 s) was not
  ident-safe, so the window moved to bars 8-9, where MAP.md shows no vocals.
