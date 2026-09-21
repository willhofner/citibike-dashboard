import CoreLocation
import SwiftUI

@MainActor
final class LocationManager: NSObject, ObservableObject {
    private let manager = CLLocationManager()

    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published var lastLocation: CLLocation?

    /// Callback for new locations — set by ContentView to persist via SwiftData
    var onLocationsReceived: (([CLLocation]) -> Void)?

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
        manager.distanceFilter = 20 // meters — balance between granularity and battery
        manager.allowsBackgroundLocationUpdates = true
        manager.pausesLocationUpdatesAutomatically = false
        manager.showsBackgroundLocationIndicator = true
        authorizationStatus = manager.authorizationStatus
    }

    func requestPermission() {
        switch authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse:
            // Upgrade to Always — iOS will show the prompt at its own timing,
            // but calling this registers our intent
            manager.requestAlwaysAuthorization()
        default:
            break
        }
    }

    func startTracking() {
        manager.startUpdatingLocation()
        // Also register for significant location changes — these wake the app
        // from suspension/termination when the user moves ~500m
        manager.startMonitoringSignificantLocationChanges()
    }

    func stopTracking() {
        manager.stopUpdatingLocation()
        manager.stopMonitoringSignificantLocationChanges()
    }
}

// MARK: - CLLocationManagerDelegate

extension LocationManager: @preconcurrency CLLocationManagerDelegate {
    nonisolated func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        Task { @MainActor in
            self.authorizationStatus = status

            switch status {
            case .authorizedWhenInUse:
                // Start tracking immediately, and request upgrade to Always
                self.startTracking()
                manager.requestAlwaysAuthorization()
            case .authorizedAlways:
                self.startTracking()
            case .denied, .restricted:
                self.stopTracking()
            default:
                break
            }
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        // Filter out low-accuracy readings (>100m is likely cell tower, not GPS)
        let goodLocations = locations.filter { $0.horizontalAccuracy <= 100 && $0.horizontalAccuracy >= 0 }
        guard !goodLocations.isEmpty else { return }

        Task { @MainActor in
            self.lastLocation = goodLocations.last
            self.onLocationsReceived?(goodLocations)
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        // Location errors are common (temporary GPS loss, etc.) — just log for now
        print("Location error: \(error.localizedDescription)")
    }
}
