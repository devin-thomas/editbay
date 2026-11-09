# Big folders (hours of footage)

1. Inventory the whole tree once (`media_probe.py DIR --json`), then work from the inventory, never from `ls`.
2. Extract audio per file on the machine that holds the files (one drive at a time: parallel reads on one HDD are
   slower, not faster).
3. Transcribe everything with turbo (fast), speaker-label if several voices matter, and keep word timestamps.
4. Write review packets: one text file per recording with `h:mm:ss | text` lines, loudness marks for energy, and
   chat or chapter markers when they exist. Read packets in full rather than grepping keywords: the good moments
   rarely contain the obvious words.
5. Nominate candidates as JSON (`in`, `out`, `quote`, `why`, `score`), merge and rank, then look at sheets for the
   top ones before choosing. A moment that needs a minute of context rarely survives into a reel.
6. Cut the selects with handles (2-3 s each side) so the editor can breathe.
