"""
Tests for the intelligent recommendation engine.
Tests Diploma Criterion 1: Practical problem-solving with intelligent recommendations.
"""

from intelligent_recommendation_engine import RecommendationGenerator

# Test data: simulated sensor anomalies
test_cases = [
    {
        'name': 'High Temperature in Server Room',
        'location_id': 1,
        'sensor_id': 1,
        'anomaly_type': 'temperature_high',
        'current_value': 28.5,
        'room_type': 'server_room',
        'description': 'Temperature exceeds normal range'
    },
    {
        'name': 'Low Humidity in Laboratory',
        'location_id': 2,
        'sensor_id': 3,
        'anomaly_type': 'humidity_low',
        'current_value': 15.0,
        'room_type': 'laboratory',
        'description': 'Humidity below normal range'
    },
    {
        'name': 'High Humidity in Office',
        'location_id': 3,
        'sensor_id': 5,
        'anomaly_type': 'humidity_high',
        'current_value': 75.0,
        'room_type': 'office',
        'description': 'Humidity above normal range'
    },
    {
        'name': 'Low Temperature in Data Center',
        'location_id': 4,
        'sensor_id': 2,
        'anomaly_type': 'temperature_low',
        'current_value': 16.0,
        'room_type': 'data_center',
        'description': 'Temperature below normal range'
    }
]

print("=" * 80)
print("TEST: INTELLIGENT RECOMMENDATION ENGINE (Diploma Criterion 1)")
print("=" * 80)

passed = 0
failed = 0

for test_case in test_cases:
    print(f"\n{'─' * 80}")
    print(f"Test: {test_case['name']}")
    print(f"Room Type: {test_case['room_type']}")
    print(f"Current Value: {test_case['current_value']}")
    print(f"{'─' * 80}")
    
    try:
        # Create generator for this room type
        generator = RecommendationGenerator(room_type=test_case['room_type'])
        
        # Generate recommendation
        recommendation = generator.generate_recommendation(
            sensor_name=f"sensor_{test_case['sensor_id']}",
            sensor_type='Temperature' if 'temperature' in test_case['anomaly_type'] else 'Humidity',
            current_value=test_case['current_value'],
            anomaly_analysis={
                'is_anomaly': True,
                'score': 0.85,
                'description': test_case['description']
            },
            measurement_history=[20.0, 21.0, 22.0, test_case['current_value']]
        )
        
        # Validate recommendation structure
        assert 'problem_description' in recommendation, "Missing problem_description"
        assert 'recommended_action' in recommendation, "Missing recommended_action"
        assert 'target_value' in recommendation, "Missing target_value"
        assert 'severity' in recommendation, "Missing severity"
        assert 'priority' in recommendation, "Missing priority"
        assert 'confidence' in recommendation, "Missing confidence"
        
        # Print results
        print(f"✅ Problem: {recommendation['problem_description']}")
        print(f"✅ Action: {recommendation['recommended_action']}")
        print(f"✅ Target Value: {recommendation['target_value']}")
        print(f"✅ Severity: {recommendation['severity']}")
        print(f"✅ Priority: {recommendation['priority']}/5")
        print(f"✅ Confidence: {recommendation['confidence']:.1%}")
        print(f"✅ Time to Target: {recommendation.get('time_to_target_minutes', 'N/A')} min")
        
        if recommendation.get('reasoning'):
            print(f"✅ Reasoning: {recommendation['reasoning']}")
        
        print(f"\n✓ PASS")
        passed += 1
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        failed += 1

print("\n" + "=" * 80)
print(f"TEST RESULTS: {passed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("✅ ALL RECOMMENDATION TESTS PASSED")
else:
    print(f"⚠️  {failed} test(s) failed")

# Test bulk generation
print("\n" + "=" * 80)
print("TEST: BULK RECOMMENDATION GENERATION")
print("=" * 80)

try:
    generator = RecommendationGenerator(room_type='server_room')
    
    sensor_readings = [
        {
            'sensor_name': 'sensor_1',
            'sensor_type': 'Temperature',
            'current_value': 28.5,
            'anomaly_analysis': {'is_anomaly': True, 'score': 0.85, 'description': 'High temp'},
            'measurement_history': [22.0, 23.0, 24.0, 28.5]
        },
        {
            'sensor_name': 'sensor_2',
            'sensor_type': 'Humidity',
            'current_value': 75.0,
            'anomaly_analysis': {'is_anomaly': True, 'score': 0.72, 'description': 'High humidity'},
            'measurement_history': [45.0, 50.0, 65.0, 75.0]
        }
    ]
    
    recommendations = generator.bulk_generate_recommendations(sensor_readings)
    
    print(f"Generated {len(recommendations)} recommendations")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. [{rec['severity'].upper()}] Priority {rec['priority']}: {rec['problem_description']}")
    
    print("\n✓ BULK GENERATION PASS")
    
except Exception as e:
    print(f"❌ BULK GENERATION FAILED: {str(e)}")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETED")
print("=" * 80)
