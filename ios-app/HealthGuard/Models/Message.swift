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
