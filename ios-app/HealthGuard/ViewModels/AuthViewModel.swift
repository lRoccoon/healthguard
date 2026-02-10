import Foundation
import Combine

/// Authentication ViewModel
class AuthViewModel: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var errorMessage: String?
    @Published var isLoading = false
    
    private let apiClient = APIClient.shared
    
    init() {
        checkAuthStatus()
    }
    
    func checkAuthStatus() {
        isAuthenticated = apiClient.authToken != nil
        
        if isAuthenticated {
            Task {
                do {
                    let user = try await apiClient.getCurrentUser()
                    await MainActor.run {
                        self.currentUser = user
                    }
                } catch {
                    await MainActor.run {
                        self.isAuthenticated = false
                        self.errorMessage = "Failed to get user info"
                    }
                }
            }
        }
    }
    
    func register(username: String, password: String, email: String?) async {
        await MainActor.run {
            isLoading = true
            errorMessage = nil
        }
        
        do {
            let user = try await apiClient.register(username: username, password: password, email: email)
            
            // Auto-login after registration
            _ = try await apiClient.login(username: username, password: password)
            
            await MainActor.run {
                self.currentUser = user
                self.isAuthenticated = true
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = error.localizedDescription
                self.isLoading = false
            }
        }
    }
    
    func login(username: String, password: String) async {
        await MainActor.run {
            isLoading = true
            errorMessage = nil
        }
        
        do {
            _ = try await apiClient.login(username: username, password: password)
            let user = try await apiClient.getCurrentUser()
            
            await MainActor.run {
                self.currentUser = user
                self.isAuthenticated = true
                self.isLoading = false
            }
        } catch {
            await MainActor.run {
                self.errorMessage = error.localizedDescription
                self.isLoading = false
            }
        }
    }
    
    func logout() {
        apiClient.authToken = nil
        currentUser = nil
        isAuthenticated = false
    }
}
