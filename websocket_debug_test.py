import requests
import json
import sys
import asyncio
import websockets
from datetime import datetime

class WebSocketDebugTester:
    def __init__(self, base_url="https://44f33d7d-8a1b-450f-af28-7e3467a6672f.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_url = base_url.replace('https', 'wss')
        self.room_id = None
        self.poll_id = None

    def create_room_and_poll(self):
        """Create a room and poll for testing"""
        print("🏗️ Creating room and poll for WebSocket testing...")
        
        # Create room
        response = requests.post(f"{self.base_url}/api/rooms/create", params={"organizer_name": "WebSocket Test"})
        if response.status_code == 200:
            self.room_id = response.json()['room_id']
            print(f"✅ Created room: {self.room_id}")
        else:
            print(f"❌ Failed to create room: {response.status_code}")
            return False

        # Create poll
        poll_data = {
            "room_id": self.room_id,
            "question": "WebSocket Test Poll",
            "options": ["Option A", "Option B"]
        }
        response = requests.post(f"{self.base_url}/api/polls/create", json=poll_data)
        if response.status_code == 200:
            self.poll_id = response.json()['poll_id']
            print(f"✅ Created poll: {self.poll_id}")
            return True
        else:
            print(f"❌ Failed to create poll: {response.status_code}")
            return False

    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        if not self.room_id:
            print("❌ No room ID for WebSocket test")
            return False

        ws_endpoint = f"{self.ws_url}/api/ws/{self.room_id}"
        print(f"🔌 Testing WebSocket connection to: {ws_endpoint}")
        
        try:
            async with websockets.connect(ws_endpoint, timeout=10) as websocket:
                print("✅ WebSocket connection established successfully!")
                
                # Test if we can receive messages
                print("📡 Waiting for WebSocket messages...")
                
                # Start the poll via API while WebSocket is connected
                print(f"🚀 Starting poll {self.poll_id} via API...")
                response = requests.post(f"{self.base_url}/api/polls/{self.poll_id}/start")
                if response.status_code == 200:
                    print("✅ Poll start API call successful")
                else:
                    print(f"❌ Poll start API call failed: {response.status_code}")
                
                # Wait for WebSocket message
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"✅ Received WebSocket message: {data}")
                    
                    if data.get('type') == 'poll_started':
                        print("🎉 Poll started WebSocket message received correctly!")
                        return True
                    else:
                        print(f"⚠️ Unexpected message type: {data.get('type')}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("❌ No WebSocket message received within timeout")
                    return False
                    
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"❌ WebSocket connection failed: {e}")
            return False
        except websockets.exceptions.InvalidURI as e:
            print(f"❌ WebSocket invalid URI: {e}")
            return False
        except Exception as e:
            print(f"❌ WebSocket connection error: {str(e)}")
            return False

    def test_poll_start_api_directly(self):
        """Test the poll start API directly"""
        if not self.poll_id:
            print("❌ No poll ID for API test")
            return False
            
        print(f"🧪 Testing poll start API directly for poll: {self.poll_id}")
        
        # Check poll status before starting
        response = requests.get(f"{self.base_url}/api/rooms/{self.room_id}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"📊 Room status before start: active_poll = {status.get('active_poll')}")
        
        # Start the poll
        response = requests.post(f"{self.base_url}/api/polls/{self.poll_id}/start")
        if response.status_code == 200:
            print("✅ Poll start API call successful")
            print(f"📝 Response: {response.json()}")
        else:
            print(f"❌ Poll start API call failed: {response.status_code}")
            return False
        
        # Check poll status after starting
        response = requests.get(f"{self.base_url}/api/rooms/{self.room_id}/status")
        if response.status_code == 200:
            status = response.json()
            active_poll = status.get('active_poll')
            print(f"📊 Room status after start: active_poll = {active_poll}")
            
            if active_poll and active_poll.get('is_active'):
                print("✅ Poll is now active in the database!")
                return True
            else:
                print("❌ Poll is not active in the database")
                return False
        else:
            print(f"❌ Failed to get room status: {response.status_code}")
            return False

    async def run_debug_tests(self):
        """Run all debug tests"""
        print("🔍 Starting WebSocket Debug Tests")
        print("=" * 50)
        
        # Step 1: Create room and poll
        if not self.create_room_and_poll():
            return False
        
        # Step 2: Test poll start API directly
        print("\n" + "=" * 30)
        api_success = self.test_poll_start_api_directly()
        
        # Step 3: Test WebSocket connection
        print("\n" + "=" * 30)
        ws_success = await self.test_websocket_connection()
        
        # Summary
        print("\n" + "=" * 50)
        print("🏁 DEBUG TEST SUMMARY")
        print("=" * 50)
        print(f"Poll Start API: {'✅ Working' if api_success else '❌ Failed'}")
        print(f"WebSocket Connection: {'✅ Working' if ws_success else '❌ Failed'}")
        
        if api_success and not ws_success:
            print("\n🎯 ROOT CAUSE IDENTIFIED:")
            print("- Poll start API works correctly")
            print("- WebSocket connection/messaging is broken")
            print("- Frontend doesn't receive poll_started messages")
            print("- UI state never updates to show active poll")
        
        return api_success and ws_success

async def main():
    """Main test function"""
    tester = WebSocketDebugTester()
    success = await tester.run_debug_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))