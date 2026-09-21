import SwiftUI
import MapKit

/// UIViewRepresentable wrapping MKMapView.
/// SwiftUI's native Map view doesn't support custom MKOverlayRenderer,
/// so we need this bridge to render the fog overlay with Core Graphics.
struct MapView: UIViewRepresentable {
    let locationPoints: [LocationPoint]
    let fogOverlay = FogOverlay()

    /// NYC-centered starting region (Manhattan)
    static let nycCenter = CLLocationCoordinate2D(latitude: 40.7580, longitude: -73.9855)
    static let nycSpan = MKCoordinateSpan(latitudeDelta: 0.12, longitudeDelta: 0.12)

    /// Constrain panning to greater NYC area
    static let nycCameraBounds = MKMapView.CameraBoundary(
        coordinateRegion: MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 40.7128, longitude: -73.9800),
            span: MKCoordinateSpan(latitudeDelta: 0.4, longitudeDelta: 0.4)
        )
    )

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator

        // Dark map style
        mapView.preferredConfiguration = {
            let config = MKStandardMapConfiguration(emphasisStyle: .muted)
            config.pointOfInterestFilter = .excludingAll
            config.showsTraffic = false
            return config
        }()
        mapView.overrideUserInterfaceStyle = .dark

        // Set initial region to Manhattan
        mapView.setRegion(
            MKCoordinateRegion(center: MapView.nycCenter, span: MapView.nycSpan),
            animated: false
        )

        // Constrain camera to NYC area
        mapView.cameraBoundary = MapView.nycCameraBounds
        mapView.cameraZoomRange = MKMapView.CameraZoomRange(
            minCenterCoordinateDistance: 500,   // closest zoom (~2 blocks)
            maxCenterCoordinateDistance: 80_000  // farthest zoom (~NYC metro)
        )

        // Show user location blue dot
        mapView.showsUserLocation = true

        // Add fog overlay (rendered below annotations, above map tiles)
        mapView.addOverlay(fogOverlay, level: .aboveRoads)

        return mapView
    }

    func updateUIView(_ mapView: MKMapView, context: Context) {
        // Update the renderer's location points and trigger a redraw
        context.coordinator.updatePoints(locationPoints, on: mapView)
    }

    // MARK: - Coordinator

    class Coordinator: NSObject, MKMapViewDelegate {
        let parent: MapView
        private var renderer: FogOverlayRenderer?

        init(_ parent: MapView) {
            self.parent = parent
        }

        func updatePoints(_ points: [LocationPoint], on mapView: MKMapView) {
            if let renderer = self.renderer {
                renderer.locationPoints = points
                renderer.setNeedsDisplay()
            }
        }

        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if overlay is FogOverlay {
                let fogRenderer = FogOverlayRenderer(overlay: overlay)
                fogRenderer.locationPoints = parent.locationPoints
                self.renderer = fogRenderer
                return fogRenderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }
    }
}
