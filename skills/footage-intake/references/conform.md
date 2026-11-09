# Conform recipes

- Variable frame rate (phone and screen recordings): `ffmpeg -i in.mp4 -fps_mode cfr -r 30 -c:v libx264 -crf 16
  -pix_fmt yuv420p -c:a aac -b:a 256k out.mp4` (use the nominal rate; 60 for 60 fps captures).
- Colour tags for HD delivery: add `-color_primaries bt709 -color_trc bt709 -colorspace bt709`. For plates going into
  a browser-rendered composition, tag the matrix only (`-colorspace bt709`): full tags make Chrome colour-manage the
  frames and they come out darker.
- Rotation: `ffmpeg -i in.mov -c:v libx264 -crf 16 -metadata:s:v:0 rotate=0 out.mp4` after the autorotate filter
  (on by default) has applied it.
- Several audio streams (OBS tracks, interviews): pick with `-map 0:a:N`; keep the others as stems if they matter.
- Frame-accurate stills: `-ss T -i SRC -frames:v 1` (seek before input is accurate in modern ffmpeg); for a range of
  exact frames use `select='between(n,A,B)'` instead of `-ss` on rounded times.
