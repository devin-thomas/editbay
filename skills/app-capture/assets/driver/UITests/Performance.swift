import ObjectiveC
import XCTest

/// Base class for scripted performances of a real app, synced to a song the app itself plays.
///
/// A take starts the song in the app, marks "song zero", then schedules every gesture on song time with `at(_:)`,
/// so the recording lines up with the soundtrack. Every action prints an `EVT` line (wall clock, song time, name,
/// point) that `tools/sim_take.py events` turns into touch overlays for the edit.
///
/// Set `APP_BUNDLE_ID` and adapt `startSong()` to the app's own path to the track (search, a row, a play button).
@MainActor
class Performance: XCTestCase {
    static let APP_BUNDLE_ID = "com.example.app"
    /// Tap call -> first audible frame, measured by syncing a take against the app's clock (0.60-0.81 s for a
    /// streamed 320 kbps MP3 on a simulator). Used until the Now Playing clock can refine it.
    static let startLatency = 0.7

    let app = XCUIApplication(bundleIdentifier: Performance.APP_BUNDLE_ID)
    var zero: Date?

    override func setUp() {
        continueAfterFailure = true
        Self.skipQuiescence()
    }

    // MARK: timing

    /// XCTest waits for the app to go idle before and after every event: 1-2 s each while music plays and counters
    /// tick, so scheduled gestures drift late and the drift accumulates. Performances skip those waits.
    nonisolated(unsafe) static var skipped = false
    static func skipQuiescence() {
        guard !skipped, let cls = NSClassFromString("XCUIApplicationProcess") else { return }
        skipped = true
        for name in ["shouldSkipPreEventQuiescence", "shouldSkipPostEventQuiescence"] {
            if let m = class_getInstanceMethod(cls, NSSelectorFromString(name)) {
                let yes: @convention(block) (AnyObject) -> Bool = { _ in true }
                method_setImplementation(m, imp_implementationWithBlock(yes))
            }
        }
        if let m = class_getInstanceMethod(cls, NSSelectorFromString("waitForQuiescenceIncludingAnimationsIdle:isPreEvent:")) {
            let none: @convention(block) (AnyObject, Bool, Bool) -> Void = { _, _, _ in }
            method_setImplementation(m, imp_implementationWithBlock(none))
        }
        if let m = class_getInstanceMethod(cls, NSSelectorFromString("waitForQuiescenceIncludingAnimationsIdle:usingActivity:isPreEvent:")) {
            let none: @convention(block) (AnyObject, Bool, AnyObject?, Bool) -> Void = { _, _, _, _ in }
            method_setImplementation(m, imp_implementationWithBlock(none))
        }
    }

    func log(_ name: String, _ p: CGPoint = .zero) {
        let now = Date()
        let s = zero.map { now.timeIntervalSince($0) } ?? -1
        print(String(format: "EVT wall=%.3f song=%.3f %@ x=%.1f y=%.1f", now.timeIntervalSince1970, s, name, p.x, p.y))
    }

    /// Waits until song time `s` (returns at once when already late; late gestures do not stack up).
    func at(_ s: Double) {
        guard let zero else { return }
        let wait = zero.addingTimeInterval(s).timeIntervalSinceNow
        if wait > 0 { Thread.sleep(forTimeInterval: wait) }
    }

    /// With Now Playing open, re-anchor song zero on the elapsed label's whole-second ticks ("0:02", "0:03", ...),
    /// keeping the earliest estimate. Blocks until the last tick checked, so schedule gestures after it.
    func refineZero(firstTick: Int = 2, extraTicks: Int = 0) {
        var best: Date?
        for k in firstTick...(firstTick + extraTicks) {
            let text = String(format: "0:%02d", k)
            let deadline = Date().addingTimeInterval(3)
            while Date() < deadline {
                let before = Date()
                if app.staticTexts[text].exists {
                    let estimate = before.addingTimeInterval(-Double(k))
                    if best == nil || estimate < best! { best = estimate }
                    break
                }
            }
        }
        if let best { zero = best; log("song.zero.refined") }
    }

    // MARK: gestures (points are in the app's coordinate space: portrait on iPhone, landscape on a landscape iPad)

    func point(_ x: Double, _ y: Double) -> XCUICoordinate {
        app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y))
    }

    func tap(_ name: String, _ x: Double, _ y: Double) {
        log(name, CGPoint(x: x, y: y)); point(x, y).tap()
    }

    func tap(_ name: String, _ element: XCUIElement) {
        let f = element.frame
        log(name, CGPoint(x: f.midX, y: f.midY)); element.tap()
    }

    /// Press, move at `velocity` points/s, release: a fling when fast, a scroll when slow. Start drags on content,
    /// never on a floating accessory (a mini player) or the gesture goes to it instead of the list.
    func drag(_ name: String, from a: (Double, Double), to b: (Double, Double), velocity: Double, hold: Double = 0) {
        log(name + ".start", CGPoint(x: a.0, y: a.1))
        point(a.0, a.1).press(forDuration: 0.02, thenDragTo: point(b.0, b.1), withVelocity: XCUIGestureVelocity(velocity), thenHoldForDuration: hold)
        log(name + ".end", CGPoint(x: b.0, y: b.1))
    }

    /// Visible typing. One typeText call per character is slow (~0.4 s each without quiescence); for a long
    /// request, type most of it in one call and the last word per character.
    func type(_ text: String, gap: Double = 0.07) {
        for ch in text { app.typeText(String(ch)); Thread.sleep(forTimeInterval: gap) }
    }

    /// The biggest hittable match: Now Playing's own Pause, not the mini player's behind the sheet.
    func largest(_ q: XCUIElementQuery) -> XCUIElement {
        let all = q.allElementsBoundByIndex.filter { $0.exists && $0.isHittable }
        return all.max { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height } ?? q.firstMatch
    }

    // MARK: app-specific entry (adapt)

    /// Search for the track, tap its row, and estimate song zero from the tap. Replace the queries with the app's.
    func startSong(query: String, rowPrefix: String, leadIn: Double = 1.5) {
        let search = app.searchFields.firstMatch
        XCTAssert(search.waitForExistence(timeout: 10))
        tap("search", search)
        type(query)
        let row = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", rowPrefix)).firstMatch
        XCTAssert(row.waitForExistence(timeout: 10))
        Thread.sleep(forTimeInterval: leadIn)
        let tapped = Date()
        tap("play.row", row)
        zero = tapped.addingTimeInterval(Self.startLatency)
        log("song.zero.estimate")
    }
}
