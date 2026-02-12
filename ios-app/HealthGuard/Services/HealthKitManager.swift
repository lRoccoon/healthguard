import Foundation
import HealthKit
import Combine

/// HealthKit Manager - Handles all HealthKit data access and permissions
class HealthKitManager: ObservableObject {
    private let healthStore = HKHealthStore()
    
    @Published var isAuthorized = false
    @Published var authorizationError: String?
    
    // Health data types we want to read
    private let typesToRead: Set<HKObjectType> = [
        HKObjectType.quantityType(forIdentifier: .stepCount)!,
        HKObjectType.quantityType(forIdentifier: .activeEnergyBurned)!,
        HKObjectType.quantityType(forIdentifier: .heartRate)!,
        HKObjectType.quantityType(forIdentifier: .appleExerciseTime)!,
        HKObjectType.quantityType(forIdentifier: .distanceWalkingRunning)!,
        HKObjectType.quantityType(forIdentifier: .flightsClimbed)!
    ]
    
    init() {
        checkAuthorizationStatus()
    }
    
    /// Check if HealthKit is available on this device
    static func isHealthDataAvailable() -> Bool {
        return HKHealthStore.isHealthDataAvailable()
    }
    
    /// Request authorization to access HealthKit data
    func requestAuthorization() {
        guard HealthKitManager.isHealthDataAvailable() else {
            authorizationError = "HealthKit is not available on this device"
            return
        }
        
        healthStore.requestAuthorization(toShare: nil, read: typesToRead) { [weak self] success, error in
            DispatchQueue.main.async {
                if let error = error {
                    self?.authorizationError = error.localizedDescription
                    self?.isAuthorized = false
                } else {
                    self?.isAuthorized = success
                    if success {
                        print("HealthKit authorization granted")
                    }
                }
            }
        }
    }
    
    /// Check current authorization status
    private func checkAuthorizationStatus() {
        let stepType = HKObjectType.quantityType(forIdentifier: .stepCount)!
        let status = healthStore.authorizationStatus(for: stepType)
        
        DispatchQueue.main.async {
            self.isAuthorized = (status == .sharingAuthorized)
        }
    }
    
    /// Fetch health data for the past 24 hours
    /// - Returns: HealthData object with collected metrics
    func fetchLast24HoursData() async throws -> HealthData {
        let calendar = Calendar.current
        let now = Date()
        let startDate = calendar.date(byAdding: .hour, value: -24, to: now)!
        
        async let steps = fetchSteps(from: startDate, to: now)
        async let activeEnergy = fetchActiveEnergy(from: startDate, to: now)
        async let heartRate = fetchHeartRate(from: startDate, to: now)
        async let exerciseTime = fetchExerciseTime(from: startDate, to: now)
        async let distance = fetchWalkingDistance(from: startDate, to: now)
        async let flights = fetchFlightsClimbed(from: startDate, to: now)
        
        let (stepsValue, energyValue, heartRateData, exerciseValue, distanceValue, flightsValue) = try await (steps, activeEnergy, heartRate, exerciseTime, distance, flights)
        
        return HealthData(
            userId: nil, // Will be set by API client
            date: now,
            steps: stepsValue,
            activeEnergy: energyValue,
            exerciseMinutes: exerciseValue,
            heartRateAvg: heartRateData.average,
            heartRateMin: heartRateData.min,
            heartRateMax: heartRateData.max,
            distanceWalking: distanceValue,
            flightsClimbed: flightsValue,
            syncedAt: Date()
        )
    }
    
    /// Fetch step count
    private func fetchSteps(from startDate: Date, to endDate: Date) async throws -> Int? {
        guard let stepType = HKQuantityType.quantityType(forIdentifier: .stepCount) else {
            return nil
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: stepType, quantitySamplePredicate: predicate, options: .cumulativeSum) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let steps = result?.sumQuantity()?.doubleValue(for: HKUnit.count())
                continuation.resume(returning: steps.map { Int($0) })
            }

            healthStore.execute(query)
        }
    }
    
    /// Fetch active energy burned
    private func fetchActiveEnergy(from startDate: Date, to endDate: Date) async throws -> Double? {
        guard let energyType = HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned) else {
            return nil
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: energyType, quantitySamplePredicate: predicate, options: .cumulativeSum) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let energy = result?.sumQuantity()?.doubleValue(for: HKUnit.kilocalorie())
                continuation.resume(returning: energy)
            }

            healthStore.execute(query)
        }
    }
    
    /// Fetch heart rate data (average, min, max)
    private func fetchHeartRate(from startDate: Date, to endDate: Date) async throws -> (average: Double?, min: Double?, max: Double?) {
        guard let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) else {
            return (nil, nil, nil)
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: heartRateType, quantitySamplePredicate: predicate, options: [.discreteAverage, .discreteMin, .discreteMax]) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let average = result?.averageQuantity()?.doubleValue(for: HKUnit(from: "count/min"))
                let min = result?.minimumQuantity()?.doubleValue(for: HKUnit(from: "count/min"))
                let max = result?.maximumQuantity()?.doubleValue(for: HKUnit(from: "count/min"))

                continuation.resume(returning: (average, min, max))
            }

            healthStore.execute(query)
        }
    }
    
    /// Fetch exercise time in minutes
    private func fetchExerciseTime(from startDate: Date, to endDate: Date) async throws -> Int? {
        guard let exerciseType = HKQuantityType.quantityType(forIdentifier: .appleExerciseTime) else {
            return nil
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: exerciseType, quantitySamplePredicate: predicate, options: .cumulativeSum) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let minutes = result?.sumQuantity()?.doubleValue(for: HKUnit.minute())
                continuation.resume(returning: minutes.map { Int($0) })
            }

            healthStore.execute(query)
        }
    }
    
    /// Fetch walking/running distance in kilometers
    private func fetchWalkingDistance(from startDate: Date, to endDate: Date) async throws -> Double? {
        guard let distanceType = HKQuantityType.quantityType(forIdentifier: .distanceWalkingRunning) else {
            return nil
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: distanceType, quantitySamplePredicate: predicate, options: .cumulativeSum) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let distance = result?.sumQuantity()?.doubleValue(for: HKUnit.meterUnit(with: .kilo))
                continuation.resume(returning: distance)
            }

            healthStore.execute(query)
        }
    }
    
    /// Fetch flights climbed
    private func fetchFlightsClimbed(from startDate: Date, to endDate: Date) async throws -> Int? {
        guard let flightsType = HKQuantityType.quantityType(forIdentifier: .flightsClimbed) else {
            return nil
        }

        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(quantityType: flightsType, quantitySamplePredicate: predicate, options: .cumulativeSum) { (query: HKStatisticsQuery, result: HKStatistics?, error: Error?) in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }

                let flights = result?.sumQuantity()?.doubleValue(for: HKUnit.count())
                continuation.resume(returning: flights.map { Int($0) })
            }

            healthStore.execute(query)
        }
    }
}
