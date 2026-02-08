import Foundation

/// HealthKit data model for syncing with backend
struct HealthData: Codable {
    let userId: String?
    let date: Date
    let steps: Int?
    let activeEnergy: Double?
    let exerciseMinutes: Int?
    let heartRateAvg: Double?
    let heartRateMin: Double?
    let heartRateMax: Double?
    let distanceWalking: Double?
    let flightsClimbed: Int?
    let syncedAt: Date?
    
    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case date
        case steps
        case activeEnergy = "active_energy"
        case exerciseMinutes = "exercise_minutes"
        case heartRateAvg = "heart_rate_avg"
        case heartRateMin = "heart_rate_min"
        case heartRateMax = "heart_rate_max"
        case distanceWalking = "distance_walking"
        case flightsClimbed = "flights_climbed"
        case syncedAt = "synced_at"
    }
}

/// Food entry model
struct FoodEntry: Codable {
    let name: String
    let description: String?
    let calories: Double?
    let giValue: String?
    let timestamp: Date
    let imageUrl: String?
    let analysis: String?
    let irAssessment: String?
    
    enum CodingKeys: String, CodingKey {
        case name
        case description
        case calories
        case giValue = "gi_value"
        case timestamp
        case imageUrl = "image_url"
        case analysis
        case irAssessment = "ir_assessment"
    }
}
