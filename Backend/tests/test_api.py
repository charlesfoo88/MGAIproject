"""
Quick test of the FastAPI endpoints
Run with: python test_api.py

Requires the API server to be running in another terminal:
uvicorn main:app --reload
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_status():
    """Test GET /api/status endpoint"""
    print("\n" + "=" * 70)
    print("TEST 1: GET /api/status")
    print("=" * 70)
    
    response = requests.get(f"{API_BASE}/api/status")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    print("✓ Status endpoint working")


def test_run_pipeline():
    """Test POST /api/run endpoint"""
    print("\n" + "=" * 70)
    print("TEST 2: POST /api/run")
    print("=" * 70)
    
    payload = {
        "match_name": "test_match_api",
        "user_preference": "I am an Arsenal fan and I love watching Saka play!"
    }
    
    print(f"Request Body:\n{json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    start_time = time.time()
    response = requests.post(f"{API_BASE}/api/run", json=payload)
    elapsed_time = time.time() - start_time
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Pipeline completed in {elapsed_time:.2f}s")
        print(f"  Status: {result['status']}")
        print(f"  Reel A captions: {len(result['reel_a_captions'])}")
        print(f"  Reel B captions: {len(result['reel_b_captions'])}")
        print(f"  Hallucinations: {result['hallucination_flagged']}")
        print(f"  Retries: {result['retry_count']}")
        print(f"  Reel A path: {result['reel_a_path']}")
        print(f"  Reel B path: {result['reel_b_path']}")
        
        # Print first caption from each reel
        if result['reel_a_captions']:
            print(f"\n  Sample Reel A caption:")
            print(f"    {result['reel_a_captions'][0]}")
        if result['reel_b_captions']:
            print(f"\n  Sample Reel B caption:")
            print(f"    {result['reel_b_captions'][0]}")
    else:
        print(f"✗ Error: {response.text}")
        raise Exception(f"Pipeline request failed with status {response.status_code}")


def test_list_videos():
    """Test GET /api/videos endpoint"""
    print("\n" + "=" * 70)
    print("TEST 3: GET /api/videos (list all)")
    print("=" * 70)
    
    response = requests.get(f"{API_BASE}/api/videos")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Found {result['count']} video files")
        for video in result['videos']:
            print(f"  - {video['filename']} ({video['size_mb']} MB)")
    else:
        print(f"Response: {response.text}")


def test_get_video():
    """Test GET /api/videos/{reel} endpoint"""
    print("\n" + "=" * 70)
    print("TEST 4: GET /api/videos/reel_a")
    print("=" * 70)
    
    # Note: This will only work if video file exists
    # In DEMO_MODE, the file won't actually exist
    response = requests.get(
        f"{API_BASE}/api/videos/reel_a",
        params={"match_name": "test_match_api"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✓ Video file available")
        print(f"  Content-Type: {response.headers.get('content-type')}")
        print(f"  Content-Length: {len(response.content)} bytes")
    elif response.status_code == 404:
        print("⚠ Video file not found (expected in DEMO_MODE)")
        print(f"  {response.json()['detail']}")
    else:
        print(f"Response: {response.text}")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MGAI API TEST SUITE")
    print("=" * 70)
    print(f"API Base URL: {API_BASE}")
    print("=" * 70)
    
    try:
        # Check if server is running
        try:
            requests.get(f"{API_BASE}/health", timeout=2)
        except requests.exceptions.ConnectionError:
            print("\n✗ ERROR: API server is not running!")
            print("\nPlease start the server first:")
            print("  cd Backend")
            print("  uvicorn main:app --reload")
            print("\nThen run this test again:")
            print("  python test_api.py")
            return
        
        # Run tests
        test_status()
        test_run_pipeline()
        test_list_videos()
        test_get_video()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
