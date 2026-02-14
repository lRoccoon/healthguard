import Foundation

/// Chat message model
struct Message: Codable, Identifiable {
    let id: UUID
    let role: MessageRole
    let content: String
    let timestamp: Date
    let attachments: [Attachment]?

    init(id: UUID = UUID(), role: MessageRole, content: String, timestamp: Date = Date(), attachments: [Attachment]? = nil) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.attachments = attachments
    }

    // Custom decoding to handle id as either String or UUID
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        // Handle id - can be String (from backend) or UUID
        if let idString = try? container.decode(String.self, forKey: .id) {
            self.id = UUID(uuidString: idString) ?? UUID()
        } else {
            self.id = try container.decode(UUID.self, forKey: .id)
        }

        self.role = try container.decode(MessageRole.self, forKey: .role)
        self.content = try container.decode(String.self, forKey: .content)
        self.timestamp = try container.decode(Date.self, forKey: .timestamp)
        self.attachments = try container.decodeIfPresent([Attachment].self, forKey: .attachments)
    }

    // Custom encoding to always send UUID as String
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id.uuidString, forKey: .id)
        try container.encode(role, forKey: .role)
        try container.encode(content, forKey: .content)
        try container.encode(timestamp, forKey: .timestamp)
        try container.encodeIfPresent(attachments, forKey: .attachments)
    }

    enum CodingKeys: String, CodingKey {
        case id, role, content, timestamp, attachments
    }
}

enum MessageRole: String, Codable {
    case user
    case assistant
    case system
}

struct Attachment: Codable {
    let type: AttachmentType
    let url: String?
    let data: Data?

    enum CodingKeys: String, CodingKey {
        case type, url, data
    }
}

enum AttachmentType: String, Codable {
    case image
    case audio
    case file
}

/// Message request/response for API
struct MessageRequest: Codable {
    let role: String
    let content: String
    let timestamp: Date?

    init(message: Message) {
        self.role = message.role.rawValue
        self.content = message.content
        self.timestamp = message.timestamp
    }
}
