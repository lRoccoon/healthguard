import Foundation

/// Session metadata model
struct SessionMetadata: Codable, Identifiable {
    let sessionId: String
    let userId: String
    let title: String?
    let createdAt: Date
    let lastMessageAt: Date
    let messageCount: Int
    let isActive: Bool

    var id: String { sessionId }

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case userId = "user_id"
        case title
        case createdAt = "created_at"
        case lastMessageAt = "last_message_at"
        case messageCount = "message_count"
        case isActive = "is_active"
    }
}

/// Full session with messages
struct Session: Codable {
    let sessionId: String
    let metadata: SessionMetadata?
    let messages: [MessageDict]

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case metadata
        case messages
    }
}

/// Untyped message dict for flexible parsing
typealias MessageDict = [String: AnyCodable]

/// Helper to support untyped JSON values
enum AnyCodable: Codable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case null
    case array([AnyCodable])
    case dictionary([String: AnyCodable])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode([AnyCodable].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: AnyCodable].self) {
            self = .dictionary(value)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Cannot decode AnyCodable")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch self {
        case .string(let value):
            try container.encode(value)
        case .int(let value):
            try container.encode(value)
        case .double(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        case .array(let value):
            try container.encode(value)
        case .dictionary(let value):
            try container.encode(value)
        }
    }

    var stringValue: String? {
        if case .string(let value) = self { return value }
        return nil
    }

    var intValue: Int? {
        if case .int(let value) = self { return value }
        return nil
    }
}
