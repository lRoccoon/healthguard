import Foundation

/// User model matching backend User schema
struct User: Codable, Identifiable {
    let id: String
    let username: String
    let email: String?
    let fullName: String?
    let createdAt: Date
    let updatedAt: Date
    let isActive: Bool
    let hasInsulinResistance: Bool
    let healthGoals: String?
    let onboardingCompleted: Bool
    let agentPersona: String?
    let preferredLanguage: String

    enum CodingKeys: String, CodingKey {
        case id = "user_id"
        case username
        case email
        case fullName = "full_name"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case isActive = "is_active"
        case hasInsulinResistance = "has_insulin_resistance"
        case healthGoals = "health_goals"
        case onboardingCompleted = "onboarding_completed"
        case agentPersona = "agent_persona"
        case preferredLanguage = "preferred_language"
    }
}

/// Login request
struct LoginRequest: Codable {
    let username: String
    let password: String
}

/// Register request
struct RegisterRequest: Codable {
    let username: String
    let password: String
    let email: String?
}

/// Token response
struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}
