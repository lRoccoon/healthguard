# iOS App Setup Guide

## Prerequisites

1. **Xcode 15.0+** installed on macOS
2. **Apple Developer Account** (for running on physical device)
3. **Physical iOS device** with iOS 16.0+ (HealthKit requires real device)

## Project Setup Steps

### 1. Create New Xcode Project

```bash
# Open Xcode and create new project:
# - Choose "App" template
# - Product Name: "HealthGuard"
# - Interface: SwiftUI
# - Language: Swift
```

### 2. Add Source Files

Copy all files from the repository structure:
- `App/` → Xcode project root
- `Models/` → Xcode project
- `Views/` → Xcode project
- `ViewModels/` → Xcode project
- `Services/` → Xcode project
- `Utils/` → Xcode project

### 3. Enable HealthKit Capability

1. Select your project in Xcode
2. Go to "Signing & Capabilities" tab
3. Click "+ Capability"
4. Add "HealthKit"
5. Check "Clinical Health Records" if needed

### 4. Configure Info.plist

Copy the provided `Info.plist` or add these keys:
- `NSHealthShareUsageDescription`
- `NSHealthUpdateUsageDescription`
- `NSMicrophoneUsageDescription`
- `NSPhotoLibraryUsageDescription`
- `NSCameraUsageDescription`

### 5. Update Backend URL

In `Constants.swift`, update the API base URL:

```swift
static let baseURL = "http://YOUR-BACKEND-URL:8000"
```

For local testing with device:
```swift
static let baseURL = "http://YOUR-MAC-IP:8000"  // e.g., "http://192.168.1.100:8000"
```

### 6. Test HealthKit Integration

#### Step 1: Request Authorization

```swift
// In HealthGuardApp.swift, onAppear:
healthKitManager.requestAuthorization()
```

#### Step 2: Fetch Data

```swift
// Example: Fetch last 24 hours of data
Task {
    let data = try await healthKitManager.fetchLast24HoursData()
    print("Steps: \(data.steps ?? 0)")
    print("Active Energy: \(data.activeEnergy ?? 0) kcal")
    print("Heart Rate Avg: \(data.heartRateAvg ?? 0) bpm")
}
```

#### Step 3: Sync with Backend

```swift
// In your ViewModel:
Task {
    let healthData = try await healthKitManager.fetchLast24HoursData()
    try await APIClient.shared.syncHealthData(healthData)
}
```

## Key Implementation Examples

### Reading Steps (Past 24 Hours)

```swift
import HealthKit

let healthStore = HKHealthStore()
let stepType = HKQuantityType.quantityType(forIdentifier: .stepCount)!

// Request authorization
healthStore.requestAuthorization(toShare: nil, read: [stepType]) { success, error in
    guard success else { return }
    
    // Create date range (last 24 hours)
    let now = Date()
    let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: now)!
    let predicate = HKQuery.predicateForSamples(withStart: yesterday, end: now)
    
    // Query steps
    let query = HKStatisticsQuery(
        quantityType: stepType,
        quantitySamplePredicate: predicate,
        options: .cumulativeSum
    ) { _, result, error in
        guard let result = result,
              let sum = result.sumQuantity() else { return }
        
        let steps = Int(sum.doubleValue(for: .count()))
        print("Steps in last 24 hours: \(steps)")
    }
    
    healthStore.execute(query)
}
```

### Reading Heart Rate

```swift
let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate)!
let predicate = HKQuery.predicateForSamples(withStart: yesterday, end: now)

let query = HKStatisticsQuery(
    quantityType: heartRateType,
    quantitySamplePredicate: predicate,
    options: [.discreteAverage, .discreteMin, .discreteMax]
) { _, result, error in
    guard let result = result else { return }
    
    let unit = HKUnit(from: "count/min")
    let avg = result.averageQuantity()?.doubleValue(for: unit)
    let min = result.minimumQuantity()?.doubleValue(for: unit)
    let max = result.maximumQuantity()?.doubleValue(for: unit)
    
    print("Heart Rate - Avg: \(avg ?? 0), Min: \(min ?? 0), Max: \(max ?? 0)")
}

healthStore.execute(query)
```

## Troubleshooting

### HealthKit Not Available
- Ensure you're testing on a physical device
- Simulator doesn't support HealthKit

### Authorization Denied
- Check if user granted permissions in Settings → Privacy → Health
- Re-request authorization if needed

### Network Errors
- Verify backend is running
- Check firewall settings
- For local testing, ensure device and Mac are on same network
- Update `baseURL` with correct IP address

## Next Steps

1. ✅ Implement full chat UI with message history *(Completed)*
2. ✅ Add voice recording with AVFoundation *(Completed - Whisper API integrated)*
3. ✅ Implement photo picker for food and medical records *(Completed - AI analysis integrated)*
4. Add local caching for offline support
5. Implement push notifications for health reminders

### Completed Features (Steps 1-3)

**Step 1: Full Chat UI** ✅
- Telegram-style message bubbles
- Multi-line text input
- Image picker and camera integration
- Voice recording UI
- HealthKit data display
- Auto-scroll and loading states

**Step 2: Voice Recording** ✅
- AVAudioRecorder integration
- Microphone permission handling
- M4A audio format output
- **OpenAI Whisper API transcription**
- Backend voice endpoint with speech-to-text
- Full voice message processing

**Step 3: Photo Analysis** ✅
- Image picker for photo library
- Camera integration for real-time capture
- **Food image analysis** (`/health/food-with-image` endpoint)
  - AI-powered food recognition
  - Automatic calorie estimation
  - GI value classification
  - IR suitability assessment
- **Medical record OCR** (enhanced `/health/medical-record` endpoint)
  - Health indicator extraction
  - Blood glucose, HbA1c, insulin parsing
  - Multimodal LLM analysis

### API Configuration

To use the new AI features, configure OpenAI API key:

```bash
# In backend/.env file
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-vision-preview  # or gpt-4o for vision + voice
```

### New Backend Endpoints

- `POST /chat/voice` - Voice message transcription and processing
- `POST /health/food-with-image` - Food image analysis
- `POST /health/medical-record` - Medical record upload with OCR (enhanced)

### Usage Examples

**Voice Message:**
- Tap and hold microphone button
- Speak your message
- Release to send
- Backend transcribes with Whisper API
- AI processes transcribed text

**Food Analysis:**
- Use "+" menu in chat
- Select "Photo Library" or "Camera"
- Take/select food photo
- Backend analyzes with Diet Agent
- Returns nutrition info and recommendations

**Medical Record:**
- Upload medical report image
- Backend extracts health indicators
- Medical Agent analyzes results
- Stores with extracted metadata

## Resources

- [HealthKit Documentation](https://developer.apple.com/documentation/healthkit)
- [SwiftUI Tutorials](https://developer.apple.com/tutorials/swiftui)
- [Combine Framework](https://developer.apple.com/documentation/combine)
