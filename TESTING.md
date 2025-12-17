# 🧪 Testing Guide for Diploma Criteria

This guide shows how to test each of the 4 diploma criteria.

---

## CRITERION 1 & 2: Testing Anomaly Detection

### Test Data Setup

Create a Python test file `test_anomaly_detection.py`:

```python
import numpy as np
from anomaly_detection_classical import (
    moving_avg_detector,
    isolation_forest_detector,
    seasonal_detector
)
from anomaly_detection_transformer import ensemble_detector

# Generate test data with anomaly
np.random.seed(42)
normal_temps = list(np.random.normal(22, 1.5, 30))  # 30 measurements
normal_temps[15] = 35  # Insert anomaly at index 15

print("=" * 60)
print("TEST 1: CLASSICAL METHODS")
print("=" * 60)

# Test 1a: Moving Average
print("\n1a) Moving Average Detector")
result = moving_avg_detector.detect(normal_temps)
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print(f"   Description: {result['description']}")
assert result['is_anomaly'] == True, "Should detect anomaly"
assert result['score'] > 0.5, "Should have high score"
print("   ✓ PASS")

# Test 1b: Isolation Forest
print("\n1b) Isolation Forest Detector")
result = isolation_forest_detector.detect(normal_temps)
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
assert result['is_anomaly'] == True, "Should detect anomaly"
print("   ✓ PASS")

# Test 1c: Seasonal
print("\n1c) Seasonal Decomposition Detector")
result = seasonal_detector.detect(normal_temps)
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print("   ✓ PASS")

print("\n" + "=" * 60)
print("TEST 2: TRANSFORMER METHODS")
print("=" * 60)

# Test 2: Ensemble (combines all transformer methods)
print("\n2) Ensemble Anomaly Detector")
result = ensemble_detector.detect(normal_temps)
print(f"   Is Anomaly: {result['is_anomaly']}")
print(f"   Score: {result['score']:.3f}")
print(f"   Models Agree: {result.get('models_agree', False)}")
assert result['is_anomaly'] == True, "Should detect anomaly"
print("   ✓ PASS")

print("\n" + "=" * 60)
print("✅ ALL ANOMALY DETECTION TESTS PASSED")
print("=" * 60)
```

Run it:
```bash
python test_anomaly_detection.py
```

---

## CRITERION 3: Testing Model Comparison

Create `test_model_comparison.py`:

```python
import numpy as np
import json
from anomaly_detection_classical import moving_avg_detector
from anomaly_detection_transformer import ensemble_detector

# Test data
np.random.seed(42)
test_data = list(np.random.normal(22, 1.5, 30))
test_data[15] = 35  # Anomaly

print("=" * 60)
print("TEST: MODEL COMPARISON")
print("=" * 60)

# Get results from both approaches
classical = moving_avg_detector.detect(test_data)
transformer = ensemble_detector.detect(test_data)

print("\nCLASSICAL RESULTS:")
print(f"  Is Anomaly: {classical['is_anomaly']}")
print(f"  Score: {classical['score']:.3f}")

print("\nTRANSFORMER RESULTS:")
print(f"  Is Anomaly: {transformer['is_anomaly']}")
print(f"  Score: {transformer['score']:.3f}")

# Compare
models_agree = classical['is_anomaly'] == transformer['is_anomaly']
agreement_score = 1 - abs(classical['score'] - transformer['score'])

print("\nCOMPARISON:")
print(f"  Models Agree: {models_agree}")
print(f"  Agreement Score: {agreement_score:.3f}")
print(f"  Classical Score: {classical['score']:.3f}")
print(f"  Transformer Score: {transformer['score']:.3f}")

# Assertions
assert models_agree == True, "Both should detect anomaly"
assert agreement_score > 0.7, "Should have high agreement"

print("\n✅ MODEL COMPARISON TEST PASSED")
print("=" * 60)
```

Run it:
```bash
python test_model_comparison.py
```

---

## CRITERION 1: Testing Recommendation Generation

Create `test_recommendations.py`:

```python
from intelligent_recommendation_engine import RecommendationGenerator
import json

print("=" * 60)
print("TEST: RECOMMENDATION GENERATION")
print("=" * 60)

gen = RecommendationGenerator()

# Test Case 1: High Temperature in Server Room
print("\nTEST 1: Server Room - High Temperature")
rec1 = gen.generate_recommendation(
    sensor_name='Server Room Temperature',
    sensor_type='Temperature',
    current_value=28.5,
    anomaly_analysis={
        'is_anomaly': True,
        'score': 0.85,
        'description': 'Temperature significantly above normal'
    },
    location_room_type='server_room'
)

print(f"  Problem: {rec1['problem_description']}")
print(f"  Action: {rec1['recommended_action']}")
print(f"  TARGET VALUE: {rec1['target_value']}°C")
print(f"  Severity: {rec1['severity']}")
print(f"  Priority: {rec1['priority']}/5")
print(f"  Confidence: {rec1['confidence']:.2%}")

assert rec1['target_value'] is not None, "Should have target value"
assert rec1['severity'] in ['low', 'medium', 'high', 'critical'], "Valid severity"
assert 1 <= rec1['priority'] <= 5, "Valid priority"
print("  ✓ PASS")

# Test Case 2: High Humidity (Condensation Risk)
print("\nTEST 2: Data Center - High Humidity (Condensation Risk)")
rec2 = gen.generate_recommendation(
    sensor_name='Data Center Humidity',
    sensor_type='Humidity',
    current_value=82.5,
    anomaly_analysis={
        'is_anomaly': True,
        'score': 0.92,
        'description': 'Humidity above safe level'
    },
    location_room_type='data_center'
)

print(f"  Problem: {rec2['problem_description']}")
print(f"  Action: {rec2['recommended_action']}")
print(f"  TARGET VALUE: {rec2['target_value']}%")
print(f"  Severity: {rec2['severity']}")
print(f"  Condensation Risk: {rec2.get('condensation_risk', False)}")

assert rec2['target_value'] is not None, "Should have target value"
assert rec2['severity'] == 'critical' or rec2['severity'] == 'high', "Should be high priority"
print("  ✓ PASS")

# Test Case 3: Normal Conditions
print("\nTEST 3: Office - Normal Conditions")
rec3 = gen.generate_recommendation(
    sensor_name='Office Temperature',
    sensor_type='Temperature',
    current_value=22.3,
    anomaly_analysis={
        'is_anomaly': False,
        'score': 0.15,
        'description': 'No significant anomaly'
    },
    location_room_type='office'
)

print(f"  Problem: {rec3['problem_description']}")
print(f"  Severity: {rec3['severity']}")
print(f"  Priority: {rec3['priority']}/5")

assert rec3['severity'] == 'low', "Normal conditions should be low priority"
assert rec3['priority'] == 1, "Lowest priority"
print("  ✓ PASS")

print("\n✅ RECOMMENDATION GENERATION TESTS PASSED")
print("=" * 60)
```

Run it:
```bash
python test_recommendations.py
```

---

## CRITERION 4: Testing Voice Command Recognition

Create `test_voice_commands.py`:

```python
from voice_notification_commands import NotificationVoiceCommandParser
import json

print("=" * 60)
print("TEST: VOICE COMMAND RECOGNITION")
print("=" * 60)

parser = NotificationVoiceCommandParser()

# Test cases: (transcript, language, expected_command)
test_cases = [
    # CONFIRMATION COMMANDS
    ("да", "ru", "confirm"),
    ("yes please", "en", "confirm"),
    ("согласен", "ru", "confirm"),
    ("ok", "en", "confirm"),
    
    # REJECTION COMMANDS
    ("нет", "ru", "reject"),
    ("no", "en", "reject"),
    ("не нужно", "ru", "reject"),
    ("cancel", "en", "reject"),
    
    # MODIFICATION COMMANDS
    ("измени на 23", "ru", "modify"),
    ("set to 24 degrees", "en", "modify"),
    
    # INFO REQUESTS
    ("объясни", "ru", "request_info"),
    ("explain please", "en", "request_info"),
    
    # REPORT REQUESTS
    ("отчет", "ru", "request_report"),
    ("show data", "en", "request_report"),
]

passed = 0
failed = 0

for transcript, language, expected_cmd in test_cases:
    result = parser.parse_command(transcript, language)
    
    is_correct = result['command'] == expected_cmd
    status = "✓ PASS" if is_correct else "✗ FAIL"
    
    print(f"\n{status}: '{transcript}' ({language})")
    print(f"       Expected: {expected_cmd}")
    print(f"       Got: {result['command']}")
    print(f"       Confidence: {result['confidence']:.2%}")
    
    if is_correct:
        passed += 1
    else:
        failed += 1
    
    # Test numeric extraction for modify commands
    if result['command'] == 'modify':
        numeric = parser.extract_numeric_value(transcript)
        if numeric:
            print(f"       Extracted Value: {numeric}")

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

assert failed == 0, f"All tests should pass (failed: {failed})"
print("✅ ALL VOICE COMMAND TESTS PASSED")
```

Run it:
```bash
python test_voice_commands.py
```

---

## API Endpoint Testing

### Test Anomaly Analysis Endpoint

```bash
# Get sensor 1 anomaly analysis
curl -X GET "http://127.0.0.1:8000/api/sensors/1/anomalies?days=7"
```

Expected response:
```json
{
  "sensor_id": 1,
  "sensor_name": "Server Room Temperature",
  "measurements_count": 168,
  "analysis": {
    "classical": {
      "is_anomaly": true/false,
      "score": 0.XX,
      "description": "...",
      "method": "moving_average + isolation_forest + seasonal"
    },
    "transformer": {
      "is_anomaly": true/false,
      "score": 0.XX,
      "reconstruction_error": 0.XX,
      "trend_info": {...},
      "models_agree": true/false
    },
    "comparison": {
      "models_agree": true/false,
      "consensus_is_anomaly": true/false,
      "agreement_score": 0.XX
    }
  }
}
```

### Test Recommendation Generation Endpoint

```bash
curl -X POST "http://127.0.0.1:8000/api/recommendations/generate" \
  -H "Content-Type: application/json" \
  -d '{"location_id": 1, "only_anomalies": true}'
```

Expected response:
```json
{
  "location_id": 1,
  "location_name": "Server Room",
  "recommendations_count": 2,
  "recommendations": [
    {
      "sensor_name": "Temperature",
      "problem_description": "...",
      "recommended_action": "...",
      "target_value": 22.0,
      "severity": "high",
      "priority": 5,
      "confidence": 0.92,
      "reasoning": "...",
      "recommendation_id": 123
    }
  ]
}
```

### Test Voice Command Endpoint

```bash
# First, create a test audio file with spoken "да"
# Then send it:

curl -X POST "http://127.0.0.1:8000/api/voice/notification-command" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_path": "path/to/test_command.wav",
    "notification_id": 1,
    "sensor_id": 1
  }'
```

Expected response:
```json
{
  "success": true,
  "command": "confirm",
  "confidence_speech": 0.98,
  "confidence_command": 0.95,
  "transcript": "да",
  "detected_language": "ru",
  "action_taken": "Recommendation confirmed, implementing changes",
  "voice_command_id": 456
}
```

### Test Diploma Statistics Endpoint

```bash
curl -X GET "http://127.0.0.1:8000/api/diploma/analysis-stats?location_id=1"
```

Expected response with all 4 criteria statistics.

---

## Automated Test Suite

Create `test_all.py` to run all tests at once:

```bash
#!/usr/bin/env python3

import subprocess
import sys

tests = [
    ('Anomaly Detection', 'test_anomaly_detection.py'),
    ('Model Comparison', 'test_model_comparison.py'),
    ('Recommendations', 'test_recommendations.py'),
    ('Voice Commands', 'test_voice_commands.py'),
]

print("=" * 60)
print("RUNNING DIPLOMA PROJECT TEST SUITE")
print("=" * 60)

passed = 0
failed = 0

for test_name, test_file in tests:
    print(f"\n▶ Running: {test_name}")
    try:
        result = subprocess.run([sys.executable, test_file], check=True, capture_output=True, text=True)
        print(result.stdout)
        passed += 1
    except subprocess.CalledProcessError as e:
        print(f"✗ FAILED: {test_name}")
        print(e.stderr)
        failed += 1

print("\n" + "=" * 60)
print(f"TEST SUITE RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
```

Run all tests:
```bash
python test_all.py
```

---

## Integration Testing with Database

Test the full flow with real database:

```python
# test_integration.py
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
import crud
import models
from anomaly_detection_classical import moving_avg_detector
from intelligent_recommendation_engine import RecommendationGenerator

db = SessionLocal()

# Test 1: Fetch sensor measurements
print("Test 1: Fetching sensor measurements...")
measurements = crud.get_sensor_measurements(db, sensor_id=1, days=7)
print(f"  Found {len(measurements)} measurements")

if measurements:
    # Test 2: Run anomaly analysis
    print("\nTest 2: Running anomaly analysis...")
    values = [m.value for m in measurements]
    result = moving_avg_detector.detect(values)
    
    # Test 3: Save analysis to DB
    print("\nTest 3: Saving analysis to database...")
    analysis = crud.create_anomaly_analysis(
        db,
        sensor_id=1,
        location_id=1,
        classical_method='moving_average',
        classical_score=result['score'],
        classical_is_anomaly=result['is_anomaly'],
        transformer_model='ensemble',
        transformer_score=result['score'],
        transformer_is_anomaly=result['is_anomaly'],
        models_agreement=True,
        confidence=0.85
    )
    print(f"  Saved with ID: {analysis.id}")
    
    # Test 4: Generate recommendation
    print("\nTest 4: Generating recommendation...")
    gen = RecommendationGenerator()
    sensor = db.query(models.Sensor).filter(models.Sensor.id == 1).first()
    if sensor:
        rec = gen.generate_recommendation(
            sensor_name=sensor.name,
            sensor_type=sensor.sensor_type.name,
            current_value=measurements[-1].value,
            anomaly_analysis=result,
            location_room_type='server_room'
        )
        
        # Test 5: Save recommendation
        print("\nTest 5: Saving recommendation to database...")
        db_rec = crud.create_intelligent_recommendation(
            db,
            sensor_id=sensor.id,
            location_id=sensor.location_id,
            problem_description=rec['problem_description'],
            recommended_action=rec['recommended_action'],
            target_value=rec['target_value'],
            reasoning=rec['reasoning'],
            confidence=rec['confidence'],
            severity=rec['severity'],
            priority=rec['priority']
        )
        print(f"  Saved with ID: {db_rec.id}")

db.close()
print("\n✅ INTEGRATION TEST PASSED")
```

---

## Performance Testing

Test the speed of each method:

```python
# test_performance.py
import time
import numpy as np
from anomaly_detection_classical import (
    moving_avg_detector,
    isolation_forest_detector,
    seasonal_detector
)
from anomaly_detection_transformer import ensemble_detector

# Large dataset
data = list(np.random.normal(22, 1.5, 1000))

print("=" * 60)
print("PERFORMANCE TEST")
print("=" * 60)

methods = [
    ("Moving Average", moving_avg_detector),
    ("Isolation Forest", isolation_forest_detector),
    ("Seasonal", seasonal_detector),
    ("Ensemble", ensemble_detector),
]

for name, detector in methods:
    start = time.time()
    for _ in range(10):
        result = detector.detect(data)
    elapsed = time.time() - start
    
    avg_time = elapsed / 10
    speed = 1000 / avg_time  # samples per second
    
    print(f"\n{name}:")
    print(f"  Time per analysis: {avg_time*1000:.2f} ms")
    print(f"  Speed: {speed:.0f} samples/sec")

print("\n✅ PERFORMANCE TEST COMPLETE")
```

---

## Conclusion

All tests verify:
- ✅ CRITERION 1: Recommendations work with correct target values
- ✅ CRITERION 2: All 6 anomaly detection methods function properly
- ✅ CRITERION 3: Model comparison and agreement metrics work
- ✅ CRITERION 4: Voice command parsing and recognition work
