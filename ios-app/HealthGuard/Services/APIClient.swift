import Foundation
import Combine

/// API Client for backend communication
class APIClient {
    static let shared = APIClient()
    
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    
    private init() {
        self.baseURL = URL(string: APIConfig.baseURL)!
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = APIConfig.timeoutInterval
        self.session = URLSession(configuration: config)
        
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            
            // ISO 8601 with fractional seconds and timezone (e.g. "2026-02-12T10:30:45.123456+00:00")
            let isoFractional = ISO8601DateFormatter()
            isoFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = isoFractional.date(from: dateString) {
                return date
            }
            
            // ISO 8601 without fractional seconds (e.g. "2026-02-12T10:30:45Z")
            let isoBasic = ISO8601DateFormatter()
            isoBasic.formatOptions = [.withInternetDateTime]
            if let date = isoBasic.date(from: dateString) {
                return date
            }
            
            // Python naive datetime with fractional seconds (e.g. "2026-02-12T10:30:45.123456")
            let df = DateFormatter()
            df.locale = Locale(identifier: "en_US_POSIX")
            df.timeZone = TimeZone(secondsFromGMT: 0)
            for fmt in ["yyyy-MM-dd'T'HH:mm:ss.SSSSSS", "yyyy-MM-dd'T'HH:mm:ss"] {
                df.dateFormat = fmt
                if let date = df.date(from: dateString) {
                    return date
                }
            }
            
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date string: \(dateString)"
            )
        }
        
        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }
    
    /// Stored auth token
    var authToken: String? {
        get { UserDefaults.standard.string(forKey: Constants.UserDefaults.authToken) }
        set { UserDefaults.standard.set(newValue, forKey: Constants.UserDefaults.authToken) }
    }
    
    // MARK: - Auth Endpoints
    
    func register(username: String, password: String, email: String?) async throws -> User {
        let request = RegisterRequest(username: username, password: password, email: email)
        return try await post(endpoint: "/auth/register", body: request)
    }
    
    func login(username: String, password: String) async throws -> TokenResponse {
        let url = baseURL.appendingPathComponent("/auth/login")
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "username", value: username),
            URLQueryItem(name: "password", value: password)
        ]
        
        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        let tokenResponse = try decoder.decode(TokenResponse.self, from: data)
        authToken = tokenResponse.accessToken
        return tokenResponse
    }
    
    func getCurrentUser() async throws -> User {
        return try await get(endpoint: "/auth/me", authenticated: true)
    }
    
    // MARK: - Chat Endpoints

    func sendMessage(_ message: Message, sessionId: String? = nil) async throws -> Message {
        let request = MessageRequest(message: message)
        var endpoint = "/chat/message"
        if let sessionId = sessionId {
            endpoint += "?session_id=\(sessionId)"
        }
        return try await post(endpoint: endpoint, body: request, authenticated: true)
    }

    func sendMessageStreaming(
        _ message: Message,
        sessionId: String? = nil,
        onRouting: @escaping (String, Double?, String) -> Void,
        onContent: @escaping (String) -> Void,
        onComplete: @escaping (String?) -> Void,
        onError: @escaping (String) -> Void
    ) {
        var urlString = baseURL.appendingPathComponent("/chat/message").absoluteString
        if let sessionId = sessionId {
            urlString += "?session_id=\(sessionId)&stream=true"
        } else {
            urlString += "?stream=true"
        }

        guard let url = URL(string: urlString) else {
            onError("Invalid URL")
            return
        }

        var headers: [String: String] = [
            "Content-Type": "application/json"
        ]

        if let token = authToken {
            headers["Authorization"] = "Bearer \(token)"
        }

        // Create request body
        let requestBody = MessageRequest(message: message)
        guard let bodyData = try? encoder.encode(requestBody) else {
            onError("Failed to encode message")
            return
        }

        // Create POST request for streaming
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = bodyData
        request.timeoutInterval = 300 // 5 minutes for long responses
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let task = session.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    onError(error.localizedDescription)
                }
                return
            }

            guard let data = data,
                  let text = String(data: data, encoding: .utf8) else {
                DispatchQueue.main.async {
                    onError("Failed to read response")
                }
                return
            }

            // Parse SSE format
            let lines = text.components(separatedBy: "\n")

            for line in lines {
                if line.hasPrefix("data: ") {
                    let jsonString = String(line.dropFirst(6))
                    if let event = StreamingEvent.parse(from: jsonString) {
                        DispatchQueue.main.async {
                            switch event {
                            case .routing(let agent, let confidence, let reason):
                                onRouting(agent, confidence, reason)
                            case .content(let content):
                                onContent(content)
                            case .done(let sessionId):
                                onComplete(sessionId)
                            case .error(let errorMsg):
                                onError(errorMsg)
                            }
                        }
                    }
                }
            }
        }

        task.resume()
    }

    func getChatHistory(days: Int = 7) async throws -> [[String: Any]] {
        var request = URLRequest(url: baseURL.appendingPathComponent("/chat/history?days=\(days)"))
        request.httpMethod = "GET"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        // Manually decode as untyped JSON since we need [[String: Any]]
        guard let jsonArray = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
            throw APIError.decodingError(NSError(domain: "APIClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to decode chat history"]))
        }

        return jsonArray
    }

    func getLastActiveSession() async throws -> Session? {
        var request = URLRequest(url: baseURL.appendingPathComponent("/chat/sessions/last/active"))
        request.httpMethod = "GET"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        // Check if response is null/empty
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           json["session"] == nil {
            return nil
        }

        return try decoder.decode(Session.self, from: data)
    }

    func listSessions(limit: Int = 20) async throws -> [SessionMetadata] {
        var request = URLRequest(url: baseURL.appendingPathComponent("/chat/sessions?limit=\(limit)"))
        request.httpMethod = "GET"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        struct SessionsResponse: Codable {
            let sessions: [SessionMetadata]
        }

        let sessionsResponse = try decoder.decode(SessionsResponse.self, from: data)
        return sessionsResponse.sessions
    }

    func getSession(sessionId: String) async throws -> Session {
        var request = URLRequest(url: baseURL.appendingPathComponent("/chat/sessions/\(sessionId)"))
        request.httpMethod = "GET"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try decoder.decode(Session.self, from: data)
    }

    func sendVoiceMessage(audioData: Data, filename: String = "audio.m4a") async throws -> Message {
        let url = baseURL.appendingPathComponent("/chat/voice")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Create multipart form data
        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add audio file
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/m4a\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try decoder.decode(Message.self, from: data)
    }

    // MARK: - Health Endpoints
    
    func syncHealthData(_ healthData: HealthData) async throws {
        let _: [String: String] = try await post(endpoint: "/health/sync-health", body: healthData, authenticated: true)
    }
    
    func logFood(_ food: FoodEntry) async throws -> FoodEntry {
        return try await post(endpoint: "/health/food", body: food, authenticated: true)
    }
    
    // MARK: - Generic Request Methods
    
    private func get<T: Decodable>(endpoint: String, authenticated: Bool = false) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(endpoint))
        request.httpMethod = "GET"
        
        if authenticated, let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try decoder.decode(T.self, from: data)
    }
    
    private func post<T: Encodable, R: Decodable>(endpoint: String, body: T, authenticated: Bool = false) async throws -> R {
        var request = URLRequest(url: baseURL.appendingPathComponent(endpoint))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if authenticated, let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        request.httpBody = try encoder.encode(body)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }
        
        return try decoder.decode(R.self, from: data)
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(Int)
    case decodingError(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError(let error):
            return "Decoding error: \(error.localizedDescription)"
        }
    }
}
