import SwiftUI

struct ContentView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @EnvironmentObject var healthKitManager: HealthKitManager
    
    var body: some View {
        Group {
            if authViewModel.isAuthenticated {
                MainTabView()
            } else {
                LoginView()
            }
        }
    }
}

/// Main tab view with chat, health, and profile tabs
struct MainTabView: View {
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ChatView()
                .tabItem {
                    Label("Chat", systemImage: "message.fill")
                }
                .tag(0)
            
            HealthView()
                .tabItem {
                    Label("Health", systemImage: "heart.fill")
                }
                .tag(1)
            
            ProfileView()
                .tabItem {
                    Label("Profile", systemImage: "person.fill")
                }
                .tag(2)
        }
    }
}

/// Login View
struct LoginView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @State private var username = ""
    @State private var password = ""
    @State private var isRegistering = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Image(systemName: "heart.text.square.fill")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 100, height: 100)
                    .foregroundColor(.red)
                
                Text("HealthGuard AI")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Text("Your Personal Health Assistant")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                TextField("Username", text: $username)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.none)
                    .padding(.horizontal)
                
                SecureField("Password", text: $password)
                    .textFieldStyle(.roundedBorder)
                    .padding(.horizontal)
                
                if let error = authViewModel.errorMessage {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption)
                }
                
                Button {
                    Task {
                        if isRegistering {
                            await authViewModel.register(username: username, password: password, email: nil)
                        } else {
                            await authViewModel.login(username: username, password: password)
                        }
                    }
                } label: {
                    if authViewModel.isLoading {
                        ProgressView()
                    } else {
                        Text(isRegistering ? "Register" : "Login")
                            .fontWeight(.semibold)
                    }
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(Color.blue)
                .foregroundColor(.white)
                .cornerRadius(Constants.UI.cornerRadius)
                .padding(.horizontal)
                .disabled(authViewModel.isLoading || username.isEmpty || password.isEmpty)
                
                Button {
                    isRegistering.toggle()
                } label: {
                    Text(isRegistering ? "Already have an account? Login" : "Don't have an account? Register")
                        .font(.footnote)
                }
                
                Spacer()
            }
            .padding()
            .navigationBarHidden(true)
        }
    }
}

/// Placeholder Chat View
struct ChatView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("Chat Interface")
                    .font(.largeTitle)
                Text("Full implementation coming in complete iOS app")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Chat")
        }
    }
}

/// Placeholder Health View
struct HealthView: View {
    @EnvironmentObject var healthKitManager: HealthKitManager
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if healthKitManager.isAuthorized {
                    Text("✅ HealthKit Authorized")
                        .foregroundColor(.green)
                    
                    Button("Sync Health Data") {
                        Task {
                            do {
                                let data = try await healthKitManager.fetchLast24HoursData()
                                print("Synced health data: \(data)")
                            } catch {
                                print("Error syncing: \(error)")
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)
                } else {
                    Text("⚠️ HealthKit Not Authorized")
                        .foregroundColor(.orange)
                    
                    Button("Request Authorization") {
                        healthKitManager.requestAuthorization()
                    }
                    .buttonStyle(.borderedProminent)
                }
                
                Text("Full health sync UI coming in complete iOS app")
                    .foregroundColor(.secondary)
            }
            .navigationTitle("Health")
        }
    }
}

/// Placeholder Profile View
struct ProfileView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                if let user = authViewModel.currentUser {
                    Text("Welcome, \(user.username)!")
                        .font(.title)
                    
                    if user.hasInsulinResistance {
                        Text("🩺 Managing Insulin Resistance")
                            .foregroundColor(.orange)
                    }
                }
                
                Button("Logout") {
                    authViewModel.logout()
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
            }
            .navigationTitle("Profile")
        }
    }
}
