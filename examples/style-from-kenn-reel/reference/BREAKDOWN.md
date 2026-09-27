# Breakdown: a 15-second single-prompt motion reel (Opus 5.5)

Reference: Kenn Ejima's post on X, 2026-09-25 (x.com/kenn/status/2103337314021937232), a 15 s 1080p60 reel made
from one prompt at Opus 5.5 xhigh, quoting kirill sh's comparison of the same prompt across two models. Studied for
its craft; its media is not reused. Numbers come from [MEASUREMENTS.md](MEASUREMENTS.md); descriptions are ours.

## Timeline

| Time (s) | Chapter | What happens | Hand-off |
|---|---|---|---|
| 0.00-1.77 | 01, a physics study | One small red dot falls onto a ruled ground line and squashes; a thin HUD readout follows its position and speed | the dot stretches into a horizontal line, then a white bloom |
| 1.77-4.23 | 02, kinetic type | On warm paper, a short statement builds word by word, each word in a different treatment: letters stepping in, a design-tool selection box, an italic serif accent word in red, letters scattering and settling | the last word multiplies into a wallpaper, then inverts to dark with red diagonal bands |
| 4.23-7.50 | 03, shape language | The last word's letters turn into dots, the dots into a row, the row into a grid; a red wave rolls through; the dots become squares, crosses, triangles in perspective | white flash |
| 7.50-~9.3 | 04, particle systems | A swirling particle cloud condenses into a thin ring | the ring thickens into a solid |
| ~9.3-11.25 | 05, material study | An iridescent torus, blobs merging into one, a sphere, a rounded cube; the HUD shows material parameters | cut |
| 11.25-11.73 | 06, easing | An easing curve plotted on paper with a dot riding it | cut on the beat |
| 11.73-13.10 | flurry | Half-beat and faster cards: op-art rings, a glitched wordmark card, an isometric voxel form, a kaleidoscope, a pixel mosaic | the mosaic clears to black |
| 13.10-15.06 | lockup | The wordmark builds, two small labels arrive, the red dot from the first frame drops in as punctuation, a quiet tagline; hold | end |

A persistent HUD frames every chapter: corner brackets, a small label top-left, format, frame rate, and BPM top-right,
a running timecode bottom-left, a progress line at the bottom, and the chapter number and name bottom-right.

## What makes it work

1. **One motif carries the piece.** The object in the first frame is the last punctuation mark. Everything between
   reads as that object's journey, so fifteen seconds of variety still feels like one idea.
2. **Each chapter is a different discipline, and says so.** Physics, type, shape, particles, materials, easing: the
   range is the message, and the HUD's chapter names turn range into intent.
3. **Hand-offs are transformations.** Dot to line, word to dots, dots to grid, particles to ring to solid. Where a
   transformation would be forced, a one-frame flash does the cut. Plain cuts are saved for the flurry.
4. **Cuts sit on the grid.** Detected tempo about 129 BPM (the HUD claims 128). After removing the detector's constant
   lag, 7 of 12 cut events land within 2 frames of a half-beat; the misses are the sub-beat flurry cuts.
5. **It accelerates, then resolves.** Cuts by third: 2, 1, 9. Development chapters of 2.5-3.7 s, a 1.4 s flurry,
   then a 2 s hold on the lockup.
6. **Density breathes.** One object, a wall of type, a grid of about a hundred, thousands of particles, one solid, a
   burst of cards, one word.
7. **Palette discipline.** Two near-blacks and a warm off-white cover about 70% of the frame; one hot red (4%) and one
   blue (3%) are the only accents, and they always mean something (the motif, an emphasis).
8. **Three type voices.** A heavy grotesk for statements, an italic serif for the one emotional word, wide-tracked
   mono for the machine layer.
9. **The HUD is a frame, not content.** Small, low contrast, always there; numbers and timecode sell precision.
10. **Mastered loud:** -12.4 LUFS, -0.6 dBTP. Platforms will turn it down; editbay targets -14 for reels.

## Signature to leave with the reference

Borrowing the principles is influence; borrowing these is a copy: the exact HUD layout and labels, the four-word
statement and its word treatments, the chapter names in this order, a red dot ending as a full stop, the specific
op-art, voxel, and kaleidoscope cards. The style skill built from this breakdown keeps principles 1-9 and makes the
motif, statement, chapters, and palette come from the brand and the subject.
