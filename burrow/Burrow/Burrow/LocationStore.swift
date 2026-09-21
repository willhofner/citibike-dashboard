import Foundation
import SwiftData
import CoreLocation
import MapKit

// MARK: - SwiftData Model

@Model
final class LocationPoint {
    var latitude: Double
    var longitude: Double
    var timestamp: Date
    var accuracy: Double

    init(latitude: Double, longitude: Double, timestamp: Date, accuracy: Double) {
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp
        self.accuracy = accuracy
    }

    convenience init(from location: CLLocation) {
        self.init(
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude,
            timestamp: location.timestamp,
            accuracy: location.horizontalAccuracy
        )
    }

    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

// MARK: - Coverage Calculator

struct CoverageCalculator {
    /// Grid cell size in degrees (~50m at NYC latitude)
    /// 1 degree latitude ≈ 111km, so 50m ≈ 0.00045 degrees
    /// 1 degree longitude at 40.7°N ≈ 84.4km, so 50m ≈ 0.00059 degrees
    static let cellSizeLat: Double = 0.00045
    static let cellSizeLon: Double = 0.00059

    /// Defogging radius in degrees (~80m = one block each side)
    static let defogRadiusLat: Double = 0.00072  // 80m in lat degrees
    static let defogRadiusLon: Double = 0.00095  // 80m in lon degrees

    /// Simplified Manhattan bounding box
    /// (A proper polygon would be more accurate, but this is fine for MVP)
    static let manhattanBounds = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 40.7831, longitude: -73.9712),
        span: MKCoordinateSpan(latitudeDelta: 0.0985, longitudeDelta: 0.0401)
    )

    static let manhattanMinLat: Double = 40.7004
    static let manhattanMaxLat: Double = 40.8821
    static let manhattanMinLon: Double = -74.0205
    static let manhattanMaxLon: Double = -73.9070

    /// Manhattan boundary polygon for more accurate coverage calculation
    static let manhattanPolygon: [CLLocationCoordinate2D] = [
        CLLocationCoordinate2D(latitude: 40.6997, longitude: -74.0205),  // Battery Park south
        CLLocationCoordinate2D(latitude: 40.7044, longitude: -74.0170),  // Battery Park west
        CLLocationCoordinate2D(latitude: 40.7418, longitude: -74.0087),  // West Village / Chelsea waterfront
        CLLocationCoordinate2D(latitude: 40.7635, longitude: -73.9977),  // Hudson Yards
        CLLocationCoordinate2D(latitude: 40.7903, longitude: -73.9790),  // Upper West Side
        CLLocationCoordinate2D(latitude: 40.8200, longitude: -73.9510),  // Harlem west
        CLLocationCoordinate2D(latitude: 40.8509, longitude: -73.9345),  // Washington Heights
        CLLocationCoordinate2D(latitude: 40.8788, longitude: -73.9218),  // Inwood west
        CLLocationCoordinate2D(latitude: 40.8821, longitude: -73.9138),  // Inwood tip
        CLLocationCoordinate2D(latitude: 40.8728, longitude: -73.9107),  // Inwood east
        CLLocationCoordinate2D(latitude: 40.8453, longitude: -73.9276),  // Washington Heights east
        CLLocationCoordinate2D(latitude: 40.8177, longitude: -73.9340),  // Harlem east (river)
        CLLocationCoordinate2D(latitude: 40.7955, longitude: -73.9291),  // East Harlem
        CLLocationCoordinate2D(latitude: 40.7640, longitude: -73.9430),  // Upper East Side
        CLLocationCoordinate2D(latitude: 40.7445, longitude: -73.9720),  // Midtown East / UN
        CLLocationCoordinate2D(latitude: 40.7280, longitude: -73.9720),  // Stuyvesant / East Village
        CLLocationCoordinate2D(latitude: 40.7105, longitude: -73.9780),  // LES waterfront
        CLLocationCoordinate2D(latitude: 40.7004, longitude: -73.9970),  // FiDi south tip
    ]

    /// Check if a coordinate is inside the Manhattan polygon (ray casting)
    static func isInsideManhattan(_ coord: CLLocationCoordinate2D) -> Bool {
        let x = coord.longitude
        let y = coord.latitude
        var inside = false
        var j = manhattanPolygon.count - 1

        for i in 0..<manhattanPolygon.count {
            let xi = manhattanPolygon[i].longitude
            let yi = manhattanPolygon[i].latitude
            let xj = manhattanPolygon[j].longitude
            let yj = manhattanPolygon[j].latitude

            if ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
                inside.toggle()
            }
            j = i
        }
        return inside
    }

    /// Calculate Manhattan coverage percentage from a set of location points
    static func calculateCoverage(points: [LocationPoint]) -> Double {
        // Build set of visited grid cells (expanded by defog radius)
        var visitedCells = Set<GridCell>()

        for point in points {
            // Calculate how many cells the defog radius covers
            let cellsLat = Int(ceil(defogRadiusLat / cellSizeLat))
            let cellsLon = Int(ceil(defogRadiusLon / cellSizeLon))

            let centerRow = Int(floor(point.latitude / cellSizeLat))
            let centerCol = Int(floor(point.longitude / cellSizeLon))

            for dr in -cellsLat...cellsLat {
                for dc in -cellsLon...cellsLon {
                    let cellLat = Double(centerRow + dr) * cellSizeLat
                    let cellLon = Double(centerCol + dc) * cellSizeLon
                    let cellCenter = CLLocationCoordinate2D(latitude: cellLat + cellSizeLat / 2, longitude: cellLon + cellSizeLon / 2)

                    if isInsideManhattan(cellCenter) {
                        visitedCells.insert(GridCell(row: centerRow + dr, col: centerCol + dc))
                    }
                }
            }
        }

        // Count total Manhattan grid cells
        let totalCells = countManhattanCells()
        guard totalCells > 0 else { return 0 }

        return Double(visitedCells.count) / Double(totalCells) * 100.0
    }

    /// Count total grid cells that fall within Manhattan polygon
    static func countManhattanCells() -> Int {
        var count = 0
        let minRow = Int(floor(manhattanMinLat / cellSizeLat))
        let maxRow = Int(floor(manhattanMaxLat / cellSizeLat))
        let minCol = Int(floor(manhattanMinLon / cellSizeLon))
        let maxCol = Int(floor(manhattanMaxLon / cellSizeLon))

        for row in minRow...maxRow {
            for col in minCol...maxCol {
                let cellCenter = CLLocationCoordinate2D(
                    latitude: Double(row) * cellSizeLat + cellSizeLat / 2,
                    longitude: Double(col) * cellSizeLon + cellSizeLon / 2
                )
                if isInsideManhattan(cellCenter) {
                    count += 1
                }
            }
        }
        return count
    }
}

// MARK: - Grid Cell (for hashing visited cells)

struct GridCell: Hashable {
    let row: Int
    let col: Int
}
