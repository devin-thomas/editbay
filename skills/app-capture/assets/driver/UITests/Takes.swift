import XCTest

/// Example takes from the Lil Gohan trailer (2026-09-29), kept as patterns. Song times are chosen from the edit's
/// beat sheet: a gesture called at `at(s)` shows on screen ~0.09 s later.
final class Takes: Performance {
    /// Phone "main": start the song, Now Playing, a home-screen visit, back in, and the pause on a beat.
    func testTakeBookends() {
        app.launch()
        Thread.sleep(forTimeInterval: 2)
        tap("tab.music", app.tabBars.buttons["Music"])
        Thread.sleep(forTimeInterval: 1)
        startSong(query: "changed my phone", rowPrefix: "Changed My Phone")
        at(0.25); openNowPlaying()
        refineZero(firstTick: 2)                      // one tick only: it blocks until "0:02"
        at(2.4); log("home.press"); XCUIDevice.shared.press(.home)
        at(5.2); let icon = XCUIApplication(bundleIdentifier: "com.apple.springboard").icons["Lil Gohan"]
        if icon.exists { tap("icon.open", icon) }
        at(24.4); openNowPlaying()
        at(30.6); let pause = largest(app.buttons.matching(identifier: "Pause"))
        at(31.17); tap("nowplaying.pause", pause)     // lands on screen at 31.26 = beat 65
        at(34.0); log("end")
    }

    /// iPad in landscape: sidebar navigation, a sidebar fold, catalog flings.
    func testTakePad() {
        XCUIDevice.shared.orientation = .landscapeLeft
        app.launch()
        Thread.sleep(forTimeInterval: 2.5)
        ensureSidebar()
        go("Music")
        startSong(query: "changed my phone", rowPrefix: "Changed My Phone")
        at(0.25); openNowPlaying()
        refineZero(firstTick: 2)
        at(7.2); tap("nowplaying.outside", 120, 900)  // a form sheet closes on a tap outside it
        at(8.0); go("Home")
        at(11.2); toggleSidebar("sidebar.hide")
        at(12.8); toggleSidebar("sidebar.show")
        at(15.05); drag("songs.fling", from: (820, 900), to: (820, 250), velocity: 5500)
        at(34.0); log("end")
    }

    // helpers specific to that app ---------------------------------------------------------------------------

    func openNowPlaying() {
        let bar = app.buttons.matching(NSPredicate(format: "label BEGINSWITH 'Player.'")).firstMatch
        tap("nowplaying.open", bar)
    }

    /// iPad: sidebar item when the sidebar shows, otherwise the floating tab bar's button.
    func go(_ dest: String) {
        let side = app.staticTexts.matching(NSPredicate(format: "label == %@", dest)).allElementsBoundByIndex.first { $0.exists && $0.isHittable && $0.frame.minX < 200 }
        if let side { tap("side." + dest.lowercased(), side); return }
        let tab = app.buttons.matching(NSPredicate(format: "label == %@", dest)).allElementsBoundByIndex.first { $0.exists && $0.isHittable && $0.frame.minY < 120 }
        if let tab { tap("tab." + dest.lowercased(), tab) }
    }

    /// iPadOS 26 names the toggle "ToggleSidebar" in the sidebar and "ToggleSideBar" in the floating tab bar.
    func toggleSidebar(_ name: String) {
        let t = app.buttons.matching(NSPredicate(format: "identifier ==[c] 'togglesidebar'")).allElementsBoundByIndex.first { $0.exists && $0.isHittable }
        if let t { tap(name, t) }
    }

    /// Sidebar visibility persists between launches; start every take from the same state.
    func ensureSidebar() {
        if app.buttons.matching(NSPredicate(format: "identifier == 'ToggleSideBar'")).firstMatch.exists {
            toggleSidebar("sidebar.restore"); Thread.sleep(forTimeInterval: 1.2)
        }
    }
}
