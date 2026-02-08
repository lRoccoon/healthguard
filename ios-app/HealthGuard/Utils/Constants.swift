import Foundation

/// API Configuration
struct APIConfig {
    /// Backend API base URL
    /// Change this to your deployed backend URL in production
    static let baseURL = "http://localhost:8000"
    
    /// API version
    static let apiVersion = "v1"
    
    /// Timeout interval for requests
    static let timeoutInterval: TimeInterval = 30
}

/// App Constants
enum Constants {
    /// UserDefaults keys
    enum UserDefaults {
        static let authToken = "auth_token"
        static let userId = "user_id"
        static let username = "username"
        static let lastSyncDate = "last_sync_date"
    }
    
    /// HealthKit related
    enum HealthKit {
        /// Number of days to sync when first connecting
        static let initialSyncDays = 7
        
        /// Sync interval in seconds
        static let syncInterval: TimeInterval = 3600 // 1 hour
    }
    
    /// UI Constants
    enum UI {
        static let cornerRadius: CGFloat = 12
        static let padding: CGFloat = 16
        static let messageBubbleMaxWidth: CGFloat = 280
    }
}
