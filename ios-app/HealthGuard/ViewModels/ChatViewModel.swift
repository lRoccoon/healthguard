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

    private var apiClient = APIClient.shared
    private var voiceRecorder = VoiceRecorder.shared

    init() {
        // Load recent messages if needed
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
            // Send message to backend
            let responseMessage = try await apiClient.sendMessage(userMessage)

            // Add assistant response
            messages.append(responseMessage)

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
            // TODO: Load chat history from backend
            // let history = try await apiClient.getChatHistory()
            // Process and display history
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

        // TODO: Send to backend for transcription and processing
        // For now, just show a placeholder response
        Task {
            isLoading = true
            do {
                // In the future, implement voice message upload to backend
                // let response = try await apiClient.sendVoiceMessage(audioData)
                // For now, show error that voice is not yet supported
                errorMessage = "Voice messages will be supported in a future update"
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
