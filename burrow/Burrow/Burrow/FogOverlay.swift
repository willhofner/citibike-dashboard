import MapKit

/// A full-screen overlay that covers the entire map with fog.
/// The renderer handles drawing the fog and punching holes where the user has been.
final class FogOverlay: NSObject, MKOverlay {
    /// Cover the entire world — MapKit clips to visible rect automatically
    let coordinate = CLLocationCoordinate2D(latitude: 0, longitude: 0)
    let boundingMapRect = MKMapRect.world
}
