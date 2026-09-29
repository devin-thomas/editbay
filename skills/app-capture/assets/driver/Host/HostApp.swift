import SwiftUI

/// Empty host: UI test bundles need one, but the performance drives the real app by bundle identifier.
@main
struct HostApp: App {
    var body: some Scene { WindowGroup { Text("Performer host") } }
}
