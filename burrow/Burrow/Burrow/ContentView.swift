import SwiftUI
import SwiftData

struct ContentView: View {
    @EnvironmentObject private var locationManager: LocationManager
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \LocationPoint.timestamp) private var locationPoints: [LocationPoint]

    @State private var coveragePercent: Double = 0
    @State private var showPermissionPrompt = false

    /// Emerald accent from web Burrow
    private let accentColor = Color(red: 0.063, green: 0.725, blue: 0.506) // #10b981

    var body: some View {
        ZStack {
            // Full-screen fog map
            MapView(locationPoints: locationPoints)
                .ignoresSafeArea()

            // Coverage % overlay — bottom center
            VStack {
                Spacer()

                HStack(spacing: 8) {
                    Image(systemName: "map.fill")
                        .font(.system(size: 14, weight: .semibold))
                    Text(String(format: "%.1f%%", coveragePercent))
                        .font(.system(size: 28, weight: .bold, design: .monospaced))
                    Text("of Manhattan")
                        .font(.system(size: 14, weight: .medium))
                        .opacity(0.7)
                }
                .foregroundColor(.white)
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(.ultraThinMaterial)
                        .environment(\.colorScheme, .dark)
                )
                .padding(.bottom, 40)
            }

            // Permission prompt overlay
            if showPermissionPrompt {
                permissionOverlay
            }
        }
        .onAppear {
            setupLocationCallbacks()
            checkPermissions()
            recalculateCoverage()
        }
        .onChange(of: locationManager.authorizationStatus) { _, newStatus in
            if newStatus == .authorizedWhenInUse || newStatus == .authorizedAlways {
                showPermissionPrompt = false
            }
        }
    }

    // MARK: - Permission Overlay

    private var permissionOverlay: some View {
        ZStack {
            Color.black.opacity(0.7)
                .ignoresSafeArea()

            VStack(spacing: 24) {
                Text("Burrow")
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(.white)

                Text("The city is covered in fog.\nShare your location to start exploring.")
                    .font(.system(size: 16))
                    .foregroundColor(.white.opacity(0.8))
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)

                Button(action: {
                    locationManager.requestPermission()
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: "location.fill")
                        Text("Start Exploring")
                    }
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 32)
                    .padding(.vertical, 14)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(accentColor)
                    )
                }
                .padding(.top, 8)
            }
            .padding(40)
        }
    }

    // MARK: - Logic

    private func setupLocationCallbacks() {
        locationManager.onLocationsReceived = { locations in
            for location in locations {
                let point = LocationPoint(from: location)
                modelContext.insert(point)
            }
            try? modelContext.save()
            recalculateCoverage()
        }
    }

    private func checkPermissions() {
        switch locationManager.authorizationStatus {
        case .notDetermined:
            showPermissionPrompt = true
        case .denied, .restricted:
            showPermissionPrompt = true
        case .authorizedWhenInUse, .authorizedAlways:
            showPermissionPrompt = false
            locationManager.startTracking()
        @unknown default:
            break
        }
    }

    private func recalculateCoverage() {
        // Run on background thread — grid calculation can be expensive with many points
        let points = locationPoints
        Task.detached {
            let coverage = CoverageCalculator.calculateCoverage(points: points)
            await MainActor.run {
                coveragePercent = coverage
            }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(LocationManager())
        .modelContainer(for: LocationPoint.self, inMemory: true)
}
