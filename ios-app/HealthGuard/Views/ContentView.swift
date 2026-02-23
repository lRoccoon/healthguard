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

/// Chat View with Telegram-style interface
struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @State private var showImageSourcePicker = false
    @State private var showImagePicker = false
    @State private var showCamera = false
    @State private var imageSourceType: UIImagePickerController.SourceType = .photoLibrary

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Messages ScrollView
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(viewModel.messages) { message in
                                MessageBubbleView(message: message)
                                    .id(message.id)
                            }

                            if viewModel.isLoading {
                                HStack {
                                    ProgressView()
                                        .padding(8)
                                    Text(viewModel.streamingStatus ?? "Thinking...")
                                        .foregroundColor(.secondary)
                                        .font(.caption)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.horizontal)
                            }
                        }
                        .padding(.vertical, 8)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        if let lastMessage = viewModel.messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }

                // Error message
                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .padding(.horizontal)
                        .padding(.vertical, 4)
                }

                // Image preview
                if let image = viewModel.selectedImage {
                    HStack {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(height: 80)
                            .cornerRadius(8)

                        Spacer()

                        Button(action: { viewModel.removeImageAttachment() }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.gray)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                    .background(Color(.systemGray6))
                }

                Divider()

                // Input toolbar
                HStack(spacing: 12) {
                    // Attachment button
                    Menu {
                        Button(action: {
                            imageSourceType = .photoLibrary
                            showImagePicker = true
                        }) {
                            Label("Photo Library", systemImage: "photo")
                        }

                        Button(action: {
                            imageSourceType = .camera
                            showCamera = true
                        }) {
                            Label("Camera", systemImage: "camera")
                        }

                        Button(action: {
                            Task { await viewModel.sendHealthKitData() }
                        }) {
                            Label("HealthKit Data", systemImage: "heart.fill")
                        }
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 28))
                            .foregroundColor(.blue)
                    }

                    // Text input
                    TextField("Message", text: $viewModel.inputText, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        .lineLimit(1...5)

                    // Voice/Send button
                    if viewModel.inputText.isEmpty && viewModel.selectedImage == nil {
                        Button(action: {
                            if viewModel.isRecording {
                                viewModel.stopVoiceRecording()
                            } else {
                                viewModel.startVoiceRecording()
                            }
                        }) {
                            Image(systemName: viewModel.isRecording ? "stop.circle.fill" : "mic.circle.fill")
                                .font(.system(size: 28))
                                .foregroundColor(viewModel.isRecording ? .red : .blue)
                        }
                    } else {
                        Button(action: {
                            Task { await viewModel.sendMessage() }
                        }) {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 28))
                                .foregroundColor(.blue)
                        }
                        .disabled(viewModel.isLoading)
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
            }
            .navigationTitle("HealthGuard AI")
            .navigationBarTitleDisplayMode(.inline)
            .sheet(isPresented: $showImagePicker) {
                ImagePicker(image: $viewModel.selectedImage, sourceType: imageSourceType)
            }
            .sheet(isPresented: $showCamera) {
                ImagePicker(image: $viewModel.selectedImage, sourceType: .camera)
            }
        }
    }
}

/// Message bubble view
struct MessageBubbleView: View {
    let message: Message

    var body: some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 50)
            }

            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 4) {
                // Message content
                Text(message.content)
                    .padding(12)
                    .background(message.role == .user ? Color.blue : Color(.systemGray5))
                    .foregroundColor(message.role == .user ? .white : .primary)
                    .cornerRadius(16)

                // Image attachments
                if let attachments = message.attachments {
                    ForEach(Array(attachments.enumerated()), id: \.offset) { index, attachment in
                        if attachment.type == .image, let data = attachment.data, let uiImage = UIImage(data: data) {
                            Image(uiImage: uiImage)
                                .resizable()
                                .scaledToFit()
                                .frame(maxWidth: 250)
                                .cornerRadius(12)
                        }
                    }
                }

                // Timestamp
                Text(message.timestamp, style: .time)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            if message.role == .assistant {
                Spacer(minLength: 50)
            }
        }
        .padding(.horizontal)
    }
}

/// Image Picker wrapper for UIKit
struct ImagePicker: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    let sourceType: UIImagePickerController.SourceType
    @Environment(\.dismiss) var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: ImagePicker

        init(_ parent: ImagePicker) {
            self.parent = parent
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let image = info[.originalImage] as? UIImage {
                parent.image = image
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
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

/// Enhanced Profile View
struct ProfileView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @EnvironmentObject var chatViewModel: ChatViewModel
    @State private var showingSessions = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if let user = authViewModel.currentUser {
                        // User Info Section
                        VStack(alignment: .leading, spacing: 12) {
                            Text("用户信息")
                                .font(.headline)
                                .foregroundColor(.secondary)

                            HStack {
                                Image(systemName: "person.circle.fill")
                                    .font(.system(size: 50))
                                    .foregroundColor(.blue)

                                VStack(alignment: .leading) {
                                    Text(user.username)
                                        .font(.title2)
                                        .bold()

                                    if let email = user.email {
                                        Text(email)
                                            .font(.subheadline)
                                            .foregroundColor(.secondary)
                                    }
                                }
                                Spacer()
                            }
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(12)

                            // Health Status
                            if user.hasInsulinResistance {
                                HStack {
                                    Image(systemName: "heart.text.square.fill")
                                        .foregroundColor(.orange)
                                    Text("正在管理胰岛素抵抗")
                                        .font(.subheadline)
                                }
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.orange.opacity(0.1))
                                .cornerRadius(8)
                            }

                            // Onboarding Status
                            HStack {
                                Image(systemName: user.onboardingCompleted ? "checkmark.circle.fill" : "circle")
                                    .foregroundColor(user.onboardingCompleted ? .green : .gray)
                                Text(user.onboardingCompleted ? "初始化已完成" : "待完成初始化")
                                    .font(.subheadline)
                            }

                            // Agent Persona
                            if let persona = user.agentPersona {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("助手角色")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    Text(persona)
                                        .font(.subheadline)
                                        .padding(8)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color(.systemGray6))
                                        .cornerRadius(6)
                                }
                            }

                            // Health Goals
                            if let goals = user.healthGoals {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("健康目标")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                    Text(goals)
                                        .font(.subheadline)
                                        .padding(8)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color(.systemGray6))
                                        .cornerRadius(6)
                                }
                            }

                            // Language
                            HStack {
                                Text("偏好语言:")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(user.preferredLanguage == "zh" ? "中文" : "English")
                                    .font(.subheadline)
                            }
                        }
                        .padding()

                        Divider()

                        // Sessions Section
                        VStack(alignment: .leading, spacing: 12) {
                            Text("会话管理")
                                .font(.headline)
                                .foregroundColor(.secondary)

                            Button(action: {
                                showingSessions = true
                                Task {
                                    await chatViewModel.loadSessions()
                                }
                            }) {
                                HStack {
                                    Image(systemName: "bubble.left.and.bubble.right")
                                    Text("查看所有会话")
                                    Spacer()
                                    Text("\(chatViewModel.sessions.count)")
                                        .foregroundColor(.secondary)
                                    Image(systemName: "chevron.right")
                                        .foregroundColor(.secondary)
                                }
                                .padding()
                                .background(Color(.systemGray6))
                                .cornerRadius(10)
                            }
                            .foregroundColor(.primary)

                            Button(action: {
                                chatViewModel.startNewSession()
                            }) {
                                HStack {
                                    Image(systemName: "plus.circle")
                                    Text("开始新会话")
                                    Spacer()
                                }
                                .padding()
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(10)
                            }
                            .foregroundColor(.blue)
                        }
                        .padding()

                        Divider()

                        // Actions
                        VStack(spacing: 12) {
                            Button("退出登录") {
                                authViewModel.logout()
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.red)
                            .frame(maxWidth: .infinity)
                        }
                        .padding()
                    }
                }
            }
            .navigationTitle("个人中心")
            .sheet(isPresented: $showingSessions) {
                SessionListView(sessions: chatViewModel.sessions)
            }
        }
    }
}

/// Session List View
struct SessionListView: View {
    let sessions: [SessionMetadata]
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationView {
            List(sessions) { session in
                VStack(alignment: .leading, spacing: 4) {
                    Text(session.title ?? "未命名会话")
                        .font(.headline)

                    HStack {
                        Text("\(session.messageCount) 条消息")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Spacer()

                        Text(formatDate(session.lastMessageAt))
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }
            .navigationTitle("所有会话")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("完成") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .short
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}
