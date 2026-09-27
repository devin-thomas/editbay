# Measurements: review.mp4

- 1920x1080 at 60.0 fps, 16.5 s
- 11 shots, 10 cut events (0 flashes), median shot 0.25 s
- cuts by third: [0, 1, 9] (acceleration when the last third dominates)
- longest shots (chapters or holds): [[0.0, 7.48], [7.48, 11.25], [13.13, 16.5], [11.48, 11.73], [12.18, 12.43], [12.88, 13.13]]
- tempo (detected): 129.2 BPM; detectors can halve or double, and lag true onsets by ~35 ms
- cuts vs half-beat grid after removing the constant offset: median |residual| 8.2 ms, 9/10 within 2 frames
- loudness: review.mp4: -16.1 LUFS, LRA 1.5 LU, TP -1.4 dBTP
- holds (static picture >= 0.4 s): [(0.0, 1.78), (1.97, 2.37), (2.43, 2.85), (2.88, 3.45), (6.1, 7.15), (7.75, 8.3), (8.3, 9.22), (9.57, 10.12), (14.12, 14.57), (14.57, 15.13), (15.13, 16.5)]
- palette: #0c1215 38% near-black, #0f171e 28% near-black, #111d2b 20% neutral, #213042 5% colour, #ebf1f3 4% near-white, #2c7be3 4% accent, #626e7e 1% neutral, #070b0f 1% near-black

## Cut timeline

```
global offset removed: +17.0 ms (median cut-to-beat delta)
cut    7.483s  half-beat delta   -40.0 ms  residual   -57.0 ms  MISS
cut   11.250s  half-beat delta   +35.0 ms  residual   +18.0 ms  ok
cut   11.483s  half-beat delta   +24.0 ms  residual    +7.0 ms  ok
cut   11.733s  half-beat delta   +30.0 ms  residual   +13.0 ms  ok
cut   11.950s  half-beat delta   +15.0 ms  residual    -2.0 ms  ok
cut   12.183s  half-beat delta   +16.0 ms  residual    -1.0 ms  ok
cut   12.433s  half-beat delta   +33.5 ms  residual   +16.5 ms  ok
cut   12.650s  half-beat delta   +18.0 ms  residual    +1.0 ms  ok
cut   12.883s  half-beat delta    +7.5 ms  residual    -9.5 ms  ok
cut   13.133s  half-beat delta   +14.0 ms  residual    -3.0 ms  ok
9/10 cuts within ±33.3 ms after offset
```

## Read next

Overview sheets: overview_01.jpg, overview_02.jpg, overview_03.jpg, overview_04.jpg, overview_05.jpg

Cut strips: strips_01.jpg, strips_02.jpg

Read them in one batch, then write the breakdown (see the reference-to-style skill).
