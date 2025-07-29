import requests
import json
import sys

class SimplePollStartTester:
    def __init__(self, base_url="https://44f33d7d-8a1b-450f-af28-7e3467a6672f.preview.emergentagent.com"):
        self.base_url = base_url
        self.room_id = None
        self.poll_id = None

    def create_room_and_poll(self):
        """Create a room and poll for testing"""
        print("🏗️ Creating room and poll for testing...")
        
        # Create room
        response = requests.post(f"{self.base_url}/api/rooms/create", params={"organizer_name": "Debug Test"})
        if response.status_code == 200:
            self.room_id = response.json()['room_id']
            print(f"✅ Created room: {self.room_id}")
        else:
            print(f"❌ Failed to create room: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

        # Create poll
        poll_data = {
            "room_id": self.room_id,
            "question": "Debug Test Poll",
            "options": ["Option A", "Option B"]
        }
        response = requests.post(f"{self.base_url}/api/polls/create", json=poll_data)
        if response.status_code == 200:
            self.poll_id = response.json()['poll_id']
            print(f"✅ Created poll: {self.poll_id}")
            return True
        else:
            print(f"❌ Failed to create poll: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    def test_poll_start_detailed(self):
        """Test the poll start with detailed debugging"""
        if not self.poll_id:
            print("❌ No poll ID for API test")
            return False
            
        print(f"\n🧪 Testing poll start API for poll: {self.poll_id}")
        
        # Step 1: Check room status before starting
        print("📊 Step 1: Checking room status before starting poll...")
        response = requests.get(f"{self.base_url}/api/rooms/{self.room_id}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   Room status: {json.dumps(status, indent=2)}")
            active_poll_before = status.get('active_poll')
            print(f"   Active poll before: {active_poll_before}")
        else:
            print(f"❌ Failed to get room status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Step 2: Start the poll
        print(f"\n🚀 Step 2: Starting poll {self.poll_id}...")
        response = requests.post(f"{self.base_url}/api/polls/{self.poll_id}/start")
        if response.status_code == 200:
            print("✅ Poll start API call successful")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Poll start API call failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Step 3: Check room status after starting
        print("\n📊 Step 3: Checking room status after starting poll...")
        response = requests.get(f"{self.base_url}/api/rooms/{self.room_id}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   Room status: {json.dumps(status, indent=2)}")
            active_poll_after = status.get('active_poll')
            print(f"   Active poll after: {active_poll_after}")
            
            if active_poll_after and active_poll_after.get('is_active'):
                print("✅ Poll is now active in the database!")
                return True
            else:
                print("❌ Poll is not active in the database")
                return False
        else:
            print(f"❌ Failed to get room status after start: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    def test_websocket_endpoint_availability(self):
        """Test if WebSocket endpoint is available via HTTP (should return 404 or method not allowed)"""
        print(f"\n🔌 Testing WebSocket endpoint availability...")
        ws_url = f"{self.base_url}/api/ws/{self.room_id}"
        print(f"   Testing: {ws_url}")
        
        # Try HTTP GET to WebSocket endpoint (should fail but tell us if endpoint exists)
        response = requests.get(ws_url)
        print(f"   HTTP GET response: {response.status_code}")
        
        if response.status_code == 404:
            print("❌ WebSocket endpoint returns 404 - endpoint not found")
            return False
        elif response.status_code == 405:
            print("✅ WebSocket endpoint exists (405 Method Not Allowed is expected for HTTP)")
            return True
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    def run_debug_tests(self):
        """Run all debug tests"""
        print("🔍 Starting Detailed Poll Start Debug Tests")
        print("=" * 60)
        
        # Step 1: Create room and poll
        if not self.create_room_and_poll():
            return False
        
        # Step 2: Test WebSocket endpoint availability
        ws_available = self.test_websocket_endpoint_availability()
        
        # Step 3: Test poll start API in detail
        api_success = self.test_poll_start_detailed()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 DETAILED DEBUG TEST SUMMARY")
        print("=" * 60)
        print(f"Room Creation: ✅ Working")
        print(f"Poll Creation: ✅ Working")
        print(f"WebSocket Endpoint: {'✅ Available' if ws_available else '❌ Not Available'}")
        print(f"Poll Start API: {'✅ Working' if api_success else '❌ Failed'}")
        
        if api_success and not ws_available:
            print("\n🎯 ISSUE IDENTIFIED:")
            print("- Poll start API works correctly and updates database")
            print("- WebSocket endpoint is not available (404 error)")
            print("- Frontend cannot receive poll_started WebSocket messages")
            print("- UI state never updates because WebSocket communication is broken")
            print("\n💡 SOLUTION NEEDED:")
            print("- Fix WebSocket endpoint configuration")
            print("- Ensure WebSocket server is properly set up")
            print("- Check if WebSocket routing is configured correctly")
        
        return api_success and ws_available

def main():
    """Main test function"""
    tester = SimplePollStartTester()
    success = tester.run_debug_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())