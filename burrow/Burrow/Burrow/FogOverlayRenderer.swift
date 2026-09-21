import MapKit
import CoreLocation

final class FogOverlayRenderer: MKOverlayRenderer {
    /// Location points to defog around — updated from ContentView
    var locationPoints: [LocationPoint] = []

    /// Defog radius in meters
    var defogRadius: CLLocationDistance = 80

    /// Maximum time gap (seconds) between consecutive points to draw a connecting trail.
    /// Points further apart than this get individual circles (prevents false trails
    /// across subway rides, drives, or gaps in recording).
    var maxTrailGap: TimeInterval = 300 // 5 minutes

    /// Fog color — semi-transparent dark overlay, matching the playful cloud aesthetic
    private let fogColor = UIColor(red: 0.15, green: 0.15, blue: 0.20, alpha: 0.88)

    override func draw(_ mapRect: MKMapRect, zoomScale: MKZoomScale, in context: CGContext) {
        // 1. Fill the entire visible rect with fog
        let rect = self.rect(for: mapRect)
        context.setFillColor(fogColor.cgColor)
        context.fill(rect)

        // 2. Switch to "clear" blend mode — everything we draw now erases the fog
        context.setBlendMode(.clear)

        guard !locationPoints.isEmpty else { return }

        // Sort points by timestamp for trail connections
        let sorted = locationPoints.sorted { $0.timestamp < $1.timestamp }

        // 3. Draw defogged circles and trails
        for i in 0..<sorted.count {
            let point = sorted[i]
            let coord = point.coordinate
            let mapPoint = MKMapPoint(coord)

            // Convert defog radius from meters to map points
            let metersPerMapPoint = MKMapPointsPerMeterAtLatitude(coord.latitude)
            let radiusInMapPoints = defogRadius * metersPerMapPoint
            let radiusInView = radiusInMapPoints * Double(zoomScale)

            // Convert center to view coordinates
            let center = self.point(for: mapPoint)

            // Draw circle at this point
            let circleRect = CGRect(
                x: center.x - radiusInView,
                y: center.y - radiusInView,
                width: radiusInView * 2,
                height: radiusInView * 2
            )
            context.fillEllipse(in: circleRect)

            // Draw connecting trail to previous point if within time threshold
            if i > 0 {
                let prev = sorted[i - 1]
                let timeDelta = point.timestamp.timeIntervalSince(prev.timestamp)

                if timeDelta <= maxTrailGap && timeDelta > 0 {
                    let prevMapPoint = MKMapPoint(prev.coordinate)
                    let prevCenter = self.point(for: prevMapPoint)

                    // Draw a thick line between the two points (same width as defog diameter)
                    context.setLineWidth(radiusInView * 2)
                    context.setLineCap(.round)
                    context.beginPath()
                    context.move(to: prevCenter)
                    context.addLine(to: center)
                    context.strokePath()
                }
            }
        }
    }
}

// MARK: - Helper

private func MKMapPointsPerMeterAtLatitude(_ latitude: Double) -> Double {
    // MKMapPoint uses a Mercator projection. At the equator, there are
    // ~6,378,137 * 2 * pi meters in the full map width of 268,435,456 points.
    // At other latitudes, meters per map point shrinks by cos(latitude).
    let mapPointsAtEquator = 268_435_456.0 / (6_378_137.0 * 2.0 * .pi)
    return mapPointsAtEquator / cos(latitude * .pi / 180.0)
}
