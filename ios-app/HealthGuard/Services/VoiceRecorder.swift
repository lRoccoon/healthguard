import Foundation
import AVFoundation
import Combine

/// Voice recorder for capturing audio messages
class VoiceRecorder: NSObject, ObservableObject {
    static let shared = VoiceRecorder()

    @Published var isRecording = false
    @Published var recordingDuration: TimeInterval = 0

    private var audioRecorder: AVAudioRecorder?
    private var recordingTimer: Timer?
    private var recordingURL: URL?

    private override init() {
        super.init()
        setupAudioSession()
    }

    private func setupAudioSession() {
        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
            try audioSession.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }

    func startRecording() throws {
        // Request microphone permission (iOS 17+ compatible)
        if #available(iOS 17.0, *) {
            AVAudioApplication.requestRecordPermission { [weak self] allowed in
                guard let self = self else { return }

                if allowed {
                    DispatchQueue.main.async {
                        do {
                            try self.beginRecording()
                        } catch {
                            print("Failed to start recording: \(error)")
                        }
                    }
                } else {
                    print("Microphone permission denied")
                }
            }
        } else {
            // Fallback for iOS 16 and earlier
            AVAudioSession.sharedInstance().requestRecordPermission { [weak self] allowed in
                guard let self = self else { return }

                if allowed {
                    DispatchQueue.main.async {
                        do {
                            try self.beginRecording()
                        } catch {
                            print("Failed to start recording: \(error)")
                        }
                    }
                } else {
                    print("Microphone permission denied")
                }
            }
        }
    }

    private func beginRecording() throws {
        // Create unique recording file
        let tempDir = FileManager.default.temporaryDirectory
        let fileName = "voice_\(UUID().uuidString).m4a"
        recordingURL = tempDir.appendingPathComponent(fileName)

        guard let url = recordingURL else { return }

        // Recording settings
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        // Create recorder
        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.delegate = self
        audioRecorder?.record()

        isRecording = true
        recordingDuration = 0

        // Start timer to update duration
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.recordingDuration = self.audioRecorder?.currentTime ?? 0
        }
    }

    func stopRecording() -> URL? {
        guard isRecording else { return nil }

        audioRecorder?.stop()
        recordingTimer?.invalidate()
        recordingTimer = nil
        isRecording = false

        return recordingURL
    }

    func cancelRecording() {
        guard isRecording else { return }

        audioRecorder?.stop()
        recordingTimer?.invalidate()
        recordingTimer = nil
        isRecording = false

        // Delete recording file
        if let url = recordingURL {
            try? FileManager.default.removeItem(at: url)
        }

        recordingURL = nil
        recordingDuration = 0
    }

    func getRecordingData(from url: URL) -> Data? {
        return try? Data(contentsOf: url)
    }
}

// MARK: - AVAudioRecorderDelegate

extension VoiceRecorder: AVAudioRecorderDelegate {
    func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        if !flag {
            print("Recording failed")
            cancelRecording()
        }
    }

    func audioRecorderEncodeErrorDidOccur(_ recorder: AVAudioRecorder, error: Error?) {
        print("Recording encoding error: \(String(describing: error))")
        cancelRecording()
    }
}
