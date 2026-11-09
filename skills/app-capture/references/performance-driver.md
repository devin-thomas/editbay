# Performance driver: patterns and traps

Measured on the Demo Artist trailer (2026-09-29, iOS 27 simulators, iPhone 17 + iPad Pro 13", Xcode 26): 5 kept takes out
of 13 recorded. Every trap below cost at least one take.

## Timing

- **Skip quiescence or nothing lands on time.** XCTest waits for the app to go idle before and after each event; a
  music app with ticking counters is never idle, so every gesture took 1-2 s and the schedule drifted by 5+ s over a
  take. `Performance.skipQuiescence()` swizzles `XCUIApplicationProcess.shouldSkipPre/PostEventQuiescence` (and the
  waits) and gestures then land within ~0.05 s of `at(s)`.
- **Call-to-screen latency ≈ 0.09 s** (tap call to the pause icon flipping). Schedule the call that much early, and draw
  touch indicators 0.09 s after the logged call.
- **Song zero.** `waitForExistence` on a Pause button detected playback 1.8 s late (it polls slowly). Use tap time +
  measured start latency (0.60-0.81 s for a streamed MP3), then `refineZero()` on the Now Playing clock. `refineZero`
  blocks until its last tick, so a take that must act at song 2.4 s refines on one tick only.
- `at(s)` never waits when already late, so one slow step delays only itself.
- Element queries cost 50-300 ms each. Resolve an element early (`let pause = largest(...)` a second before) and tap it
  on time.

## Gestures

- **Flings start on content, not on floating chrome.** A drag starting at y=740 on an iPhone 17 landed on the mini player
  and scrolled nothing. Start around y=640 and end near y=130 at 5000-6500 pt/s for a fast catalog fling; 250-400 pt/s
  reads as a deliberate scroll.
- **Getting back to the top of a long list:** tap the status bar's clock area (x≈52, y≈22 on iPhone), not its centre;
  the centre (x≈201, y≈14) expands the Dynamic Island's live Now Playing instead, which is a great shot on purpose.
  Or fling back (drag 200 → 700 at 7000 pt/s) until the target is hittable.
- **Dismiss taps must land on static text** (a header, a large title). A "tap away" at the top hit the search field; a
  tap mid-screen hit a song row and raised "Replace what's playing?".
- **Typing:** per-character `typeText` is ~0.4 s/char without quiescence; long strings look slow. Type most in one call.
- **Swipe actions** need the row fully above floating chrome, or the revealed buttons are hidden.

## App and platform state

- **Search persists** across tab switches; clear it before browsing or the "fling through the catalog" scrolls one
  result. iPhone: the search "Close" button; iPad (search in the navigation bar): "Clear text".
- **iPad sidebar state persists** between launches; start each take with `ensureSidebar()`. iPadOS 26 names the toggle
  `ToggleSidebar` (sidebar) and `ToggleSideBar` (floating tab bar). With the sidebar hidden, destinations are top tab
  bar buttons; `go()` handles both. A form sheet (Now Playing on iPad) closes on a tap outside it.
- **Landscape coordinates:** after `XCUIDevice.shared.orientation = .landscapeLeft`, element frames and taps are in
  landscape points (1376×1032 on an iPad Pro 13"); the recording file is stored portrait with a rotation tag (ffmpeg
  auto-rotates on decode).
- **Home screen:** `XCUIDevice.shared.press(.home)` shows iOS's own close animation into the app icon, which leads
  naturally into a push on the icon. The springboard is `XCUIApplication(bundleIdentifier: "com.apple.springboard")`.
- Some screens change the audio (a radio station, a video): film them in a separate take and use them only where no
  clock is visible, or not at all.
- A failed test can leave xcodebuild collecting diagnostics for minutes: `take.sh` has a watchdog.

## Probe first

Before a take, run a probe test that prints `app.debugDescription` (and `frame` of the buttons you will touch) for each
screen: labels differ from what you expect ("Close" not "Cancel"; tab buttons named by title; iPad sidebar rows are
static texts).
