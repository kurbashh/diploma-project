import numpy as np
from anomaly_detection_classical import (
    moving_avg_detector,
    isolation_forest_detector,
    seasonal_detector
)
from anomaly_detection_transformer import ensemble_detector

# Generate test data with anomaly - more realistic data
np.random.seed(42)
# Create a larger dataset: 100 normal measurements around 22°C
normal_temps = list(np.random.normal(22, 1.5, 100))  # 100 measurements
# Insert anomaly at index 50
normal_temps[50] = 35

print("=" * 60)
print("TEST 1: CLASSICAL METHODS")
print("=" * 60)

# Test 1a: Moving Average
print("\n1a) Moving Average Detector")
# Use the measurements up to and including the anomaly
test_data = normal_temps[:51]  # 51 measurements (50 normal + 1 anomaly)
result = moving_avg_detector.detect_anomaly(test_data[:-1], test_data[-1])
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print(f"   Description: {result['description']}")
print(f"   Deviation: {result.get('deviation', 0):.2f}°C")
print("   ✓ Test completed")

# Test 1b: Isolation Forest
print("\n1b) Isolation Forest Detector")
test_data = normal_temps[:51]
result = isolation_forest_detector.detect_anomaly(test_data)
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print("   ✓ Test completed")

# Test 1c: Seasonal
print("\n1c) Seasonal Decomposition Detector")
from datetime import datetime
test_data = normal_temps[:51]
result = seasonal_detector.detect_anomaly(datetime.now(), test_data[-1])
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print("   ✓ Test completed")

print("\n" + "=" * 60)
print("TEST 2: TRANSFORMER METHODS")
print("=" * 60)

# Test 2: Ensemble (combines all transformer methods)
print("\n2) Ensemble Anomaly Detector")
test_data = normal_temps[:51]
# Pass measurements (excluding last) and current value separately
result = ensemble_detector.detect_anomaly(test_data[:-1], test_data[-1])
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print(f"   Models Agree: {result.get('models_agree', False)}")
print("   ✓ Test completed")

print("\n" + "=" * 60)
print("✅ ALL ANOMALY DETECTION TESTS COMPLETED SUCCESSFULLY")
print("=" * 60)
print("=" * 60)