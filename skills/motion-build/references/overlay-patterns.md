# Overlay patterns

| Pattern | When | How (scaffold kind or custom) |
|---|---|---|
| Glass card beside the face | a name, product, or claim while a person talks | `side-card` in the free zone on the side they point or look toward; icon + title + subtitle |
| Word highlight band | the line that is the point of the video | `word-highlight` in `bottom`: each word's marker grows as it is spoken |
| Lower third | who is speaking, where, a source | `lower-third`; hold the brand's read time |
| Step card + rail | teaching a sequence | `step` cards on one side with a `custom` rail of all steps on top, the active step lit |
| Bullet build | a list the voice walks through | `bullet`; items stagger on their anchors |
| Proof panel | "prove it on screen" | `image-panel` with a real screenshot or screen recording and an honest label |
| Takeover | a chapter change, a big number, an end card | `takeover` (`zone: full`, `cover_face` when over footage) |
| Round pip face-cam | course-style: talking head shrinks to a corner over slides | custom: wrap the base video in a div and animate the wrapper's scale and x/y into a circle mask; never animate the timed video element itself |
| Split whiteboard | explain-it-simply edits | custom: left half a drawing surface (SVG paths revealed with stroke-dashoffset), right half the speaker |
| HUD frame | showreels and motion-design pieces, only when the brand allows it | `--hud "LABEL"`: corner brackets, a label, a frame-accurate timecode |
| Captions | accessibility and shorts | `--captions WORDS`: 7 words or 34 characters per line, breaks at pauses, marker per word |

Legibility over footage: text never sits on moving footage without a card, a shadow band, or a dim behind it.
Phone check: the smallest text must still read on a 390 px wide preview.

## Vertical re-layout

1. Treat 9:16 as a new layout: with a 1920px-tall canvas, stack content between y=160 and y=1500 (about 8.3%-78.1%),
   scale type for a phone, and leave the bottom ~20% clear for platform UI. Example: `--remap left=upper,right=lower`
   uses the portrait safe stack; keep a background plane with a slow gradient or glow for depth instead of a flat void.
