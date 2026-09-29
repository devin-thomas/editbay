import XCTest
import ObjectiveC

/// Real, scripted performances of the Lil Gohan app for the trailer. Each take starts "Changed My Phone 📲 Remix!"
/// from the search results and then acts on song time (seconds since playback began), so the footage lines up with
/// the song. Every action prints an EVT line (wall clock, song time, name, point) for syncing ripples in the edit.
@MainActor
class Performance: XCTestCase {
    let app = XCUIApplication(bundleIdentifier: "com.lilgohan.listen")
    var zero: Date?

    override func setUp() {
        continueAfterFailure = true
        Self.skipQuiescence()
    }

    /// XCTest waits for the app to go idle before and after every event (1-2 s each here, because the app is never idle
    /// while music plays and counters tick). A performance needs gestures on the beat, so the takes skip those waits.
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

    /// Waits until song time `s`.
    func at(_ s: Double) {
        guard let zero else { return }
        let wait = zero.addingTimeInterval(s).timeIntervalSinceNow
        if wait > 0 { Thread.sleep(forTimeInterval: wait) }
    }

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

    /// A finger drag: press, move at `velocity` points/s, release (a fling when fast).
    func drag(_ name: String, from a: (Double, Double), to b: (Double, Double), velocity: Double, hold: Double = 0) {
        log(name + ".start", CGPoint(x: a.0, y: a.1))
        point(a.0, a.1).press(forDuration: 0.02, thenDragTo: point(b.0, b.1), withVelocity: XCUIGestureVelocity(velocity), thenHoldForDuration: hold)
        log(name + ".end", CGPoint(x: b.0, y: b.1))
    }

    func type(_ text: String, gap: Double = 0.07) {
        for ch in text { app.typeText(String(ch)); Thread.sleep(forTimeInterval: gap) }
    }

    func songRow() -> XCUIElement {
        app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Changed My Phone'")).firstMatch
    }

    /// Search, tap the song, confirm if asked, and mark song zero when the player reports playing.
    func startSong(query: String = "changed my phone", leadIn: Double = 1.5) {
        let search = app.searchFields.firstMatch
        XCTAssert(search.waitForExistence(timeout: 10))
        tap("search", search)
        type(query)
        let row = songRow()
        XCTAssert(row.waitForExistence(timeout: 10))
        Thread.sleep(forTimeInterval: leadIn)
        let tapped = Date()
        tap("play.row", row)
        zero = tapped.addingTimeInterval(Self.startLatency)
        log("song.zero.estimate")
        let playNow = app.buttons["Play Now"]
        if playNow.exists { tap("play.confirm", playNow); zero = Date().addingTimeInterval(Self.startLatency - 0.3) }
    }

    /// Measured on take A1: 0.81 s from the tap call to the first audible frame (clock sync against the recording).
    static let startLatency = 0.81

    /// With Now Playing open, re-anchors song zero on the clock's "0:0N" tick (the label changes at whole seconds).
    func refineZero(on label: String, seconds: Double, extraTicks: Int = 2) {
        var best: Date?
        for k in Int(seconds)...(Int(seconds) + extraTicks) {
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

    /// The biggest matching element (Now Playing's control, not the mini player's behind the sheet).
    func largest(_ q: XCUIElementQuery) -> XCUIElement {
        let all = q.allElementsBoundByIndex.filter { $0.exists && $0.isHittable }
        return all.max { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height } ?? q.firstMatch
    }

    /// Taps a Browse segment; if it scrolled away, flings back toward the top first.
    func segment(_ name: String, seekLimit: Int = 3) {
        let b = app.buttons[name].firstMatch
        for _ in 0..<seekLimit where !(b.exists && b.isHittable) {
            drag("seg.seek", from: (201, 200), to: (201, 700), velocity: 7000)
            Thread.sleep(forTimeInterval: 0.25)
        }
        if b.exists { tap("seg." + name.lowercased(), b) }
    }

    /// iPad: a destination from the sidebar when it is showing, otherwise from the floating tab bar.
    func go(_ dest: String) {
        let side = app.staticTexts.matching(NSPredicate(format: "label == %@", dest)).allElementsBoundByIndex.first { $0.exists && $0.isHittable && $0.frame.minX < 200 }
        if let side { tap("side." + dest.lowercased(), side); return }
        let tab = app.buttons.matching(NSPredicate(format: "label == %@", dest)).allElementsBoundByIndex.first { $0.exists && $0.isHittable && $0.frame.minY < 120 }
        if let tab { tap("tab." + dest.lowercased(), tab); return }
        let any = app.tabBars.buttons[dest].firstMatch
        if any.exists { tap("tabbar." + dest.lowercased(), any) }
    }

    /// iPad sidebar toggle: "ToggleSidebar" in the sidebar, "ToggleSideBar" in the floating tab bar.
    func toggleSidebar(_ name: String) {
        let t = app.buttons.matching(NSPredicate(format: "identifier ==[c] 'togglesidebar'")).allElementsBoundByIndex.first { $0.exists && $0.isHittable }
        if let t { tap(name, t) }
    }

    func ensureSidebar() {
        if app.buttons.matching(NSPredicate(format: "identifier == 'ToggleSideBar'")).firstMatch.exists { toggleSidebar("sidebar.restore"); Thread.sleep(forTimeInterval: 1.2) }
    }

    func closeSearch() {
        let close = app.buttons["Close"].firstMatch
        if close.exists && close.isHittable { tap("search.close", close); return }
        let clear = app.buttons["Clear text"].firstMatch
        if clear.exists { tap("search.clear", clear) }
    }

    func openNowPlaying() {
        let bar = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Player.'")).firstMatch
        tap("nowplaying.open", bar)
    }
}

final class Takes: Performance {
    /// iPhone main: cold open, Now Playing, Home, full-catalog flings, segments, back to Now Playing, pause after the hook.
    func testTakeA() {
        app.launch()
        Thread.sleep(forTimeInterval: 2)
        tap("tab.music", app.tabBars.buttons["Music"])
        Thread.sleep(forTimeInterval: 1)
        startSong()
        at(0.25); openNowPlaying()
        refineZero(on: "0:02", seconds: 2.0)
        at(8.4); drag("nowplaying.dismiss", from: (201, 160), to: (201, 820), velocity: 3000)
        at(9.3); tap("tab.home", app.tabBars.buttons["Home"])
        at(10.4); drag("home.scroll", from: (201, 640), to: (201, 400), velocity: 260)
        at(12.4); drag("home.scroll2", from: (201, 400), to: (201, 660), velocity: 320)
        at(13.6); tap("tab.music", app.tabBars.buttons["Music"])
        at(14.2); closeSearch()
        at(15.05); drag("songs.fling", from: (201, 640), to: (201, 130), velocity: 5200)
        at(16.30); drag("songs.fling2", from: (201, 640), to: (201, 130), velocity: 6500)
        at(17.55); tap("statusbar.top", 52, 22)
        at(18.60); segment("Albums")
        at(19.25); drag("albums.fling", from: (201, 640), to: (201, 150), velocity: 4200)
        at(20.40); tap("statusbar.top", 52, 22)
        at(21.10); segment("Collections")
        at(21.60); drag("collections.fling", from: (201, 640), to: (201, 150), velocity: 4200)
        at(22.50); tap("statusbar.top", 52, 22)
        at(23.10); segment("Producers")
        at(23.55); drag("producers.fling", from: (201, 640), to: (201, 130), velocity: 5500)
        at(24.2); openNowPlaying()
        at(30.6); let big = largest(app.buttons.matching(identifier: "Pause"))
        at(31.12); tap("nowplaying.pause", big)
        at(34.0); log("end")
    }

    /// iPhone features: swipe and context actions, Dynamic Island, Ask, Videos, Radio tab, stats, sleep timer, Up Next.
    func testTakeB() {
        app.launch()
        Thread.sleep(forTimeInterval: 2)
        tap("tab.music", app.tabBars.buttons["Music"])
        Thread.sleep(forTimeInterval: 1)
        startSong()
        at(1.0); closeSearch()
        at(2.2); let row = app.buttons.matching(NSPredicate(format: "label BEGINSWITH '100%'")).firstMatch
        if row.exists {
            let f = row.frame
            drag("row.swipe", from: (f.maxX - 24, f.midY), to: (f.minX + 150, f.midY), velocity: 800)
        }
        at(4.0); let header = app.staticTexts["663 songs"].firstMatch
        if header.exists { tap("swipe.dismiss", header) }
        at(5.0); let row2 = app.buttons.matching(NSPredicate(format: "label BEGINSWITH '11 to 9'")).firstMatch
        if row2.exists { let f = row2.frame; log("row.longpress", CGPoint(x: f.midX, y: f.midY)); row2.press(forDuration: 0.8) }
        at(7.4); tap("menu.dismiss", 201, 140)
        at(8.2); tap("tab.home", app.tabBars.buttons["Home"])
        at(9.0); tap("island.expand", 201, 14)
        at(11.4); let title = app.navigationBars.staticTexts["Home"].firstMatch
        if title.exists { tap("island.dismiss", title) } else { tap("island.dismiss", 60, 140) }
        at(12.0); tap("tab.music", app.tabBars.buttons["Music"])
        at(12.8); tap("ask.open", app.navigationBars.buttons["Ask"].firstMatch)
        at(13.0); let field = app.textFields.firstMatch
        if field.waitForExistence(timeout: 2) { tap("ask.field", field); type("late night pluggnb for the drive", gap: 0.045) }
        at(15.4); let suggest = app.buttons["Suggest a queue"].firstMatch
        if suggest.exists { tap("ask.suggest", suggest) }
        at(21.5); drag("ask.scroll", from: (201, 640), to: (201, 300), velocity: 900)
        at(23.0); let close = app.buttons["Close"].firstMatch
        if close.exists { tap("ask.close", close) }
        at(24.0); tap("tab.videos", app.tabBars.buttons["Videos"])
        at(25.0); drag("videos.scroll", from: (201, 640), to: (201, 300), velocity: 1500)
        at(26.2); tap("tab.radio", app.tabBars.buttons["Radio"])
        at(27.6); tap("tab.home", app.tabBars.buttons["Home"])
        at(28.3); let listening = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Your listening'")).firstMatch
        if listening.exists { tap("stats.open", listening) }
        at(29.6); drag("stats.scroll", from: (201, 640), to: (201, 220), velocity: 1400)
        at(31.0); drag("stats.scroll2", from: (201, 640), to: (201, 220), velocity: 1400)
        at(32.4); openNowPlaying()
        at(34.0); let sleep = app.buttons.matching(NSPredicate(format: "label CONTAINS 'Sleep'")).firstMatch
        if sleep.exists { tap("sleep.menu", sleep) }
        at(35.6); let m30 = app.buttons["30 minutes"].firstMatch
        if m30.exists { tap("sleep.30", m30) }
        at(37.0); let upnext = app.buttons["Up Next"].firstMatch
        if upnext.exists { tap("upnext.open", upnext) }
        at(40.0); log("end")
    }

    /// iPad landscape main: sidebar, Now Playing, Home, sidebar collapse and return, catalog flings, an album, Videos,
    /// Now Playing again, pause after the hook.
    func testTakeC() {
        XCUIDevice.shared.orientation = .landscapeLeft
        app.launch()
        Thread.sleep(forTimeInterval: 2.5)
        ensureSidebar()
        go("Music")
        Thread.sleep(forTimeInterval: 1)
        startSong()
        at(0.25); openNowPlaying()
        refineZero(on: "0:02", seconds: 2.0)
        at(7.2); tap("nowplaying.outside", 120, 900)
        at(8.0); go("Home")
        at(9.2); drag("home.scroll", from: (820, 800), to: (820, 520), velocity: 300)
        at(11.2); toggleSidebar("sidebar.hide")
        at(12.8); toggleSidebar("sidebar.show")
        at(13.9); go("Music")
        at(14.5); closeSearch()
        at(15.05); drag("songs.fling", from: (820, 900), to: (820, 250), velocity: 5500)
        at(16.4); drag("songs.fling2", from: (820, 900), to: (820, 250), velocity: 6500)
        at(17.5); segment("Albums", seekLimit: 7)
        at(18.3); drag("albums.fling", from: (820, 900), to: (820, 380), velocity: 2600)
        at(19.6); let album = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Dragon Rush 4'")).allElementsBoundByIndex.first { $0.exists && $0.isHittable }
        if let album { tap("album.open", album) }
        at(21.8); drag("album.scroll", from: (820, 800), to: (820, 450), velocity: 700)
        at(23.0); go("Videos")
        at(24.0); openNowPlaying()
        at(31.12); let big = largest(app.buttons.matching(identifier: "Pause"))
        tap("nowplaying.pause", big)
        at(34.0); log("end")
    }

    /// iPhone bookends: tap to play, Now Playing, home screen (icon), back into the app, Home, Now Playing, pause on beat 65.
    func testTakeE() {
        app.launch()
        Thread.sleep(forTimeInterval: 2)
        tap("tab.music", app.tabBars.buttons["Music"])
        Thread.sleep(forTimeInterval: 1)
        startSong()
        at(0.25); openNowPlaying()
        refineZero(on: "0:02", seconds: 2.0, extraTicks: 0)
        at(2.4); log("home.press"); XCUIDevice.shared.press(.home)
        at(5.2); let icon = XCUIApplication(bundleIdentifier: "com.apple.springboard").icons["Lil Gohan"]
        if icon.exists { tap("icon.open", icon) }
        at(7.0); drag("nowplaying.dismiss", from: (201, 160), to: (201, 820), velocity: 3000)
        at(7.8); tap("tab.home", app.tabBars.buttons["Home"])
        at(9.0); drag("home.scroll", from: (201, 640), to: (201, 380), velocity: 240)
        at(11.6); drag("home.scroll2", from: (201, 640), to: (201, 360), velocity: 300)
        at(14.0); drag("home.scroll3", from: (201, 300), to: (201, 760), velocity: 900)
        at(15.0); tap("tab.music", app.tabBars.buttons["Music"])
        at(15.6); closeSearch()
        at(16.4); drag("songs.fling", from: (201, 640), to: (201, 130), velocity: 6000)
        at(17.7); drag("songs.fling2", from: (201, 640), to: (201, 130), velocity: 6500)
        at(19.2); tap("tab.videos", app.tabBars.buttons["Videos"])
        at(20.6); tap("tab.home", app.tabBars.buttons["Home"])
        at(24.4); openNowPlaying()
        at(30.6); let big = largest(app.buttons.matching(identifier: "Pause"))
        at(31.17); tap("nowplaying.pause", big)
        at(34.0); log("end")
    }
}
