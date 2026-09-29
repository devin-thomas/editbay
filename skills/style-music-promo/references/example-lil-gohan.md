# Worked example: the Lil Gohan app trailer (2026-09-29)

Brief: a 30-40 s "Coming Soon™" trailer for the Lil Gohan iPhone/iPad app, on the artist's "Changed My Phone 📲 Remix!",
the song literally playing from the app, a liquid-glass 3D app icon that fills with aqua, iPad shown with real taps,
Uppercut Labs at the end; then a 9:16 cut for Shorts/TikTok/Reels. Records and code: editbay `examples/lil-gohan-trailer/`.

## What the map said

125.0 BPM (period 0.48005 s), first beat 0.058 s. Bars 1-8 intro (vocals + melody, no drums), bars 9-16 hook (808 on
beat 1 of odd bars and beat 2 of even bars, clap on beat 3, 8th hats), bars 17-18 break (drums and bass out), bar 19
the verse. The owner counted "the first sixteen" and "the second sixteen": 8 bars each in 4/4 at this tempo. Lyric
anchors in the hook: "I changed my phone" (song 25.10-25.80 s) and "had to change my phone" (28.54-29.64 s).

## Decisions that made it work

- The song starts at T 1.442 so beat 0 lands at T 1.500: every beat is 1.5 + 0.48005k in the edit.
- The cold open is a macro on the song row and mini player: the real tap, then the play icon flips to pause on the
  first note, then the camera pulls back. Frame 0 is the app, not black.
- The icon push: iOS's own close animation shrinks the app into its home-screen icon; the edit pushes into that icon and
  cuts under a flash to the glass icon's first frame at the same size.
- The drop coincides with the camera diving into the aqua liquid, then a white flash into the cover wall; the phone's
  catalog fling was scheduled to already be moving on the downbeat.
- Real taps on the beat: Albums on bar 11's downbeat, Collections on its clap, the iPad sidebar folding on bar 12's clap.
- The lyric does the device swaps; the flurry sits in bar 15; the second lyric swap brings back the phone for the pause.
- The pause (song 31.313 s, 53 ms after beat 65) stops the music; a quarter-note echo of "slam" rings under the lockup;
  "Lil Gohan", "Coming Soon™", "iPhone · iPad" land on echoes 2, 3, 4; the ident lands on bar 19's downbeat. (They were
  keyed to stop + k beats, the ends of the repeat windows; `echo_tail --json` now gives the audible hits, 0.31 s
  earlier: T 33.406, 33.886, 34.366.)

## What it cost

13 simulator takes (5 kept), three rounds of timestamp fixes on the simulator video, one full plate re-render (light
blob), 16 → 32 → 16 spp. Blender plates were the long pole: ~900 frames per aspect at ~7-12 s each on an M5 Max; the
HyperFrames render of the whole piece took 2-3 min.
