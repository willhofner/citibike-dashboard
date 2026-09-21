import SwiftUI
import SwiftData

@main
struct BurrowApp: App {
    @StateObject private var locationManager = LocationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(locationManager)
        }
        .modelContainer(for: LocationPoint.self)
    }
}
