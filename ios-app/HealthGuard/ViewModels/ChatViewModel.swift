import SwiftUI
import Combine

@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var inputText: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var selectedImage: UIImage?
    @Published var showImagePicker: Bool = false
    @Published var showCamera: Bool = false
    @Published var isRecording: Bool = false
    @Published var currentSessionId: String?
    @Published var sessions: [SessionMetadata] = []

    private var apiClient = APIClient.shared
    private var voiceRecorder = VoiceRecorder.shared

    init() {
        // Load last active session on init
        Task {
            await loadLastActiveSession()
        }
    }

    func loadLastActiveSession() async {
        do {
            guard let session = try await apiClient.getLastActiveSession() else {
                // No previous session, start fresh
                return
            }

            // Set current session ID
            currentSessionId = session.sessionId

            // Convert message dicts to Message objects
            var loadedMessages: [Message] = []
            for messageDict in session.messages {
                if let role = messageDict["role"]?.stringValue,
                   let content = messageDict["content"]?.stringValue {
                    let messageRole: MessageRole
                    switch role {
                    case "user":
                        messageRole = .user
                    case "assistant":
                        messageRole = .assistant
                    case "system":
                        messageRole = .system
                    default:
                        continue
                    }

                    let timestamp: Date
                    if let timestampStr = messageDict["timestamp"]?.stringValue {
                        let formatter = ISO8601DateFormatter()
                        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
                        timestamp = formatter.date(from: timestampStr) ?? Date()
                    } else {
                        timestamp = Date()
                    }

                    let message = Message(
                        role: messageRole,
                        content: content,
                        timestamp: timestamp
                    )
                    loadedMessages.append(message)
                }
            }

            messages = loadedMessages
        } catch {
            // Silently fail - user can start a new session
            print("Failed to load last session: \(error.localizedDescription)")
        }
    }

    func startNewSession() {
        messages.removeAll()
        currentSessionId = nil
    }

    func loadSessions() async {
        do {
            sessions = try await apiClient.listSessions(limit: 20)
        } catch {
            errorMessage = "Failed to load sessions: \(error.localizedDescription)"
        }
    }

    func sendMessage() async {
        guard !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        let messageText = inputText
        inputText = ""

        // Add user message to UI immediately
        var attachments: [Attachment]? = nil
        if let image = selectedImage {
            // Create attachment for the image
            if let imageData = image.jpegData(compressionQuality: 0.8) {
                attachments = [Attachment(type: .image, url: nil, data: imageData)]
            }
        }

        let userMessage = Message(
            role: .user,
            content: messageText,
            timestamp: Date(),
            attachments: attachments
        )
        messages.append(userMessage)

        isLoading = true
        errorMessage = nil

        do {
            // Send message to backend with current session ID
            let responseMessage = try await apiClient.sendMessage(userMessage, sessionId: currentSessionId)

            // Add assistant response
            messages.append(responseMessage)

            // If this was a new session, we should get the session_id back
            // For now, we'll rely on the backend to handle session continuity

            // Clear selected image after successful send
            selectedImage = nil
            isLoading = false
        } catch {
            errorMessage = "Failed to send message: \(error.localizedDescription)"
            isLoading = false
        }
    }

    func loadChatHistory() async {
        do {
            // Load chat history from backend
            let history = try await apiClient.getChatHistory()

            // Process and display history - merge with existing messages
            // The history comes in as an array of session dictionaries
            for session in history {
                if let messagesArray = session["messages"] as? [[String: Any]] {
                    for messageDict in messagesArray {
                        if let role = messageDict["role"] as? String,
                           let content = messageDict["content"] as? String {
                            let messageRole: MessageRole
                            switch role {
                            case "user":
                                messageRole = .user
                            case "assistant":
                                messageRole = .assistant
                            case "system":
                                messageRole = .system
                            default:
                                continue
                            }

                            let timestamp: Date
                            if let timestampStr = messageDict["timestamp"] as? String {
                                let formatter = ISO8601DateFormatter()
                                formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
                                timestamp = formatter.date(from: timestampStr) ?? Date()
                            } else {
                                timestamp = Date()
                            }

                            let message = Message(
                                role: messageRole,
                                content: content,
                                timestamp: timestamp
                            )
                            messages.append(message)
                        }
                    }
                }
            }
        } catch {
            errorMessage = "Failed to load chat history: \(error.localizedDescription)"
        }
    }

    func addImageAttachment(_ image: UIImage) {
        selectedImage = image
    }

    func removeImageAttachment() {
        selectedImage = nil
    }

    func startVoiceRecording() {
        do {
            try voiceRecorder.startRecording()
            isRecording = true
        } catch {
            errorMessage = "Failed to start recording: \(error.localizedDescription)"
        }
    }

    func stopVoiceRecording() {
        guard let recordingURL = voiceRecorder.stopRecording() else {
            isRecording = false
            return
        }

        isRecording = false

        // Get audio data
        guard let audioData = voiceRecorder.getRecordingData(from: recordingURL) else {
            errorMessage = "Failed to read recording"
            return
        }

        // Create message with audio attachment
        let audioMessage = Message(
            role: .user,
            content: "[Voice message \(String(format: "%.1f", voiceRecorder.recordingDuration))s]",
            timestamp: Date(),
            attachments: [Attachment(type: .audio, url: nil, data: audioData)]
        )
        messages.append(audioMessage)

        // Send to backend for transcription and processing
        Task {
            isLoading = true
            errorMessage = nil

            do {
                // Get filename from recording URL
                let filename = recordingURL.lastPathComponent

                // Send voice message to backend
                let responseMessage = try await apiClient.sendVoiceMessage(
                    audioData: audioData,
                    filename: filename
                )

                // Add assistant response
                messages.append(responseMessage)
                isLoading = false
            } catch {
                errorMessage = "Failed to send voice message: \(error.localizedDescription)"
                isLoading = false
            }
        }
    }

    func sendHealthKitData() async {
        do {
            // Fetch health data from HealthKit
            let healthKitManager = HealthKitManager.shared
            let healthData = try await healthKitManager.fetchLast24HoursData()

            // Format health data as a message
            var dataText = "📊 HealthKit Data (Last 24 hours):\n\n"
            dataText += "🚶 Steps: \(healthData.steps ?? 0)\n"
            dataText += "🔥 Active Energy: \(String(format: "%.1f", healthData.activeEnergy ?? 0)) kcal\n"
            dataText += "⏱ Exercise: \(healthData.exerciseMinutes ?? 0) min\n"

            if let hrAvg = healthData.heartRateAvg {
                dataText += "❤️ Heart Rate (avg): \(Int(hrAvg)) bpm\n"
            }
            if let distance = healthData.distanceWalking {
                dataText += "🏃 Distance: \(String(format: "%.2f", distance)) km\n"
            }
            if let flights = healthData.flightsClimbed {
                dataText += "🪜 Flights: \(flights)\n"
            }

            // Send as user message
            let healthMessage = Message(
                role: .user,
                content: dataText,
                timestamp: Date()
            )
            messages.append(healthMessage)
            inputText = "Analyze my health data"

            await sendMessage()
        } catch {
            errorMessage = "Failed to fetch HealthKit data: \(error.localizedDescription)"
        }
    }

    func clearMessages() {
        messages.removeAll()
    }
}
