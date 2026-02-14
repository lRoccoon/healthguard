import SwiftUI

@main
struct HealthGuardApp: App {
    @StateObject private var authViewModel = AuthViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(authViewModel)
                .environmentObject(HealthKitManager.shared)
                .onAppear {
                    // Request HealthKit permissions on app launch
                    HealthKitManager.shared.requestAuthorization()
                }
        }
    }
}
