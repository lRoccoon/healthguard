import SwiftUI

@main
struct HealthGuardApp: App {
    @StateObject private var authViewModel = AuthViewModel()
    @StateObject private var healthKitManager = HealthKitManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authViewModel)
                .environmentObject(healthKitManager)
                .onAppear {
                    // Request HealthKit permissions on app launch
                    healthKitManager.requestAuthorization()
                }
        }
    }
}
