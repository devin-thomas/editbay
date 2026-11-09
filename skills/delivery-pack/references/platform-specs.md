# Platform notes (checked 2026-09-26; recheck before relying on them)

- **YouTube uploads:** H.264 High profile, closed GOP, BT.709, AAC-LC or Opus 48 kHz stereo (Google's encoding
  recommendations). 60 fps masters are fine; 4K uploads get a better-quality encode on YouTube's side. YouTube does not
  publish a loudness target; -14 LUFS integrated is an industry observation, and narrated explainers read better at
  -16 with true peak at or below -1 dBTP.
- **Chapters:** timestamps in the description, the first at 0:00, at least three, each at least 10 seconds long.
- **Captions:** SRT or VTT upload; from verified word timings, 1-2 lines, about 32-42 characters per line. Validate
  the assembled display line after cue breaks, and keep a compound such as `Large-scale` joined rather than rendering
  `Large -scale`.
- **Shorts:** vertical or square, up to 3 minutes. Keep text inside the middle of the frame: the right edge carries
  buttons and the bottom carries the caption and channel line (safe-zone figures are third-party guidance, unverified).
- **Thumbnails:** 1280x720 (16:9), JPG or PNG under 2 MB. Frame candidates are a start; designed ones perform better.
- **Disclosure:** state synthetic or cloned voices and realistic generated media in the description; YouTube also has an
  altered-or-synthetic content setting at upload.
