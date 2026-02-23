import Foundation

/// Simple Server-Sent Events (SSE) client for streaming chat responses
class EventSource {
    private var task: URLSessionDataTask?
    private var onMessage: ((String) -> Void)?
    private var onComplete: (() -> Void)?
    private var onError: ((Error) -> Void)?

    private let url: URL
    private let headers: [String: String]

    init(url: URL, headers: [String: String] = [:]) {
        self.url = url
        self.headers = headers
    }

    func onMessage(_ handler: @escaping (String) -> Void) {
        self.onMessage = handler
    }

    func onComplete(_ handler: @escaping () -> Void) {
        self.onComplete = handler
    }

    func onError(_ handler: @escaping (Error) -> Void) {
        self.onError = handler
    }

    func connect() {
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 300 // 5 minutes

        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        let session = URLSession.shared
        task = session.dataTask(with: request) { [weak self] data, response, error in
            if let error = error {
                self?.onError?(error)
                return
            }

            guard let data = data else { return }

            // Parse SSE data
            if let text = String(data: data, encoding: .utf8) {
                self?.parseSSE(text)
            }
        }

        task?.resume()
    }

    private func parseSSE(_ text: String) {
        let lines = text.components(separatedBy: "\n")
        var currentEvent = ""

        for line in lines {
            if line.hasPrefix("data: ") {
                let data = String(line.dropFirst(6))
                currentEvent = data
                onMessage?(currentEvent)
            } else if line.isEmpty && !currentEvent.isEmpty {
                currentEvent = ""
            }
        }

        onComplete?()
    }

    func close() {
        task?.cancel()
        task = nil
    }
}

/// Streaming chat event types
enum StreamingEvent {
    case routing(agent: String, confidence: Double?, reason: String)
    case content(String)
    case done(sessionId: String?)
    case error(String)

    static func parse(from jsonString: String) -> StreamingEvent? {
        guard let data = jsonString.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            return nil
        }

        switch type {
        case "routing":
            let agent = json["agent"] as? String ?? "unknown"
            let confidence = json["confidence"] as? Double
            let reason = json["reason"] as? String ?? ""
            return .routing(agent: agent, confidence: confidence, reason: reason)

        case "content":
            let content = json["content"] as? String ?? ""
            return .content(content)

        case "done":
            let sessionId = json["session_id"] as? String
            return .done(sessionId: sessionId)

        case "error":
            let error = json["error"] as? String ?? "Unknown error"
            return .error(error)

        default:
            return nil
        }
    }
}
