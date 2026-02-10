# iOS HealthGuard App

This is the iOS client application for HealthGuard AI, built with SwiftUI.

## Features

- 💬 Chat interface for interacting with AI health assistant
- 🏥 HealthKit integration for automatic health data sync
- 🎤 Voice input support using AVFoundation
- 📸 Photo upload for food and medical record analysis
- 📊 Daily health logs and trends visualization

## Requirements

- iOS 16.0+
- Xcode 15.0+
- Swift 5.9+

## Project Structure

```
ios-app/HealthGuard/
├── App/
│   ├── HealthGuardApp.swift         # App entry point
│   └── AppDelegate.swift            # App delegate
├── Models/
│   ├── User.swift                   # User model
│   ├── Message.swift                # Chat message model
│   └── HealthData.swift             # Health data models
├── Views/
│   ├── ChatView.swift               # Main chat interface
│   ├── HealthSyncView.swift         # Health data sync UI
│   └── ProfileView.swift            # User profile
├── ViewModels/
│   ├── ChatViewModel.swift          # Chat logic
│   └── HealthViewModel.swift        # Health data logic
├── Services/
│   ├── APIClient.swift              # Backend API client
│   ├── HealthKitManager.swift       # HealthKit integration
│   ├── AudioRecorder.swift          # Voice recording
│   └── PhotoPicker.swift            # Photo selection
└── Utils/
    ├── Constants.swift              # App constants
    └── Extensions.swift             # Swift extensions
```

## Setup

1. Open `HealthGuard.xcodeproj` in Xcode
2. Update the backend API URL in `Constants.swift`
3. Enable HealthKit capability in project settings
4. Run on a physical device (HealthKit requires real device)

## HealthKit Permissions

The app requests the following HealthKit permissions:
- Steps
- Active Energy
- Heart Rate
- Exercise Time
- Walking/Running Distance

## Backend Integration

The app communicates with the FastAPI backend via REST API:
- Base URL: `http://localhost:8000` (development)
- Authentication: JWT Bearer token
- Endpoints: `/auth/*`, `/chat/*`, `/health/*`
