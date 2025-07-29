#!/usr/bin/env python3
"""
Comprehensive Secret Poll Backend API Test Suite
Tests all major endpoints and functionality systematically
"""

import requests
import json
import sys
import time
import websocket
import threading
from datetime import datetime
import uuid

class ComprehensiveAPITester:
    def __init__(self, base_url="https://44f33d7d-8a1b-450f-af28-7e3467a6672f.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.room_id = None
        self.participant_tokens = []
        self.participant_ids = []
        self.poll_ids = []
        self.organizer_name = f"Test Organizer {datetime.now().strftime('%H%M%S')}"
        self.websocket_messages = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                if data:
                    response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, params=params, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except:
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {error_data}")
                except:
                    self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}: {response.text[:100]}")
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test 1: Health Check Endpoint"""
        print("\n🔍 Testing Health Check Endpoint")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success and response.get('status') == 'healthy'

    def test_room_creation_and_management(self):
        """Test 2: Room Creation and Management"""
        print("\n🔍 Testing Room Creation and Management")
        
        # Test basic room creation
        success, response = self.run_test(
            "Create Room",
            "POST",
            "api/rooms/create",
            200,
            params={"organizer_name": self.organizer_name}
        )
        if not success:
            return False
        
        self.room_id = response.get('room_id')
        if not self.room_id:
            self.log_test("Room ID Assignment", False, "No room_id in response")
            return False
        
        self.log_test("Room ID Assignment", True, f"Room ID: {self.room_id}")
        
        # Test custom room ID creation
        custom_id = f"TEST{datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Room with Custom ID",
            "POST",
            "api/rooms/create",
            200,
            params={"organizer_name": f"{self.organizer_name} Custom", "custom_room_id": custom_id}
        )
        if not success:
            return False
        
        # Test duplicate custom ID (should fail)
        success, response = self.run_test(
            "Create Room with Duplicate Custom ID (Should Fail)",
            "POST",
            "api/rooms/create",
            400,
            params={"organizer_name": "Another Organizer", "custom_room_id": custom_id}
        )
        if not success:
            return False
        
        # Test room status
        success, response = self.run_test(
            "Get Room Status",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if not success:
            return False
        
        # Verify required fields in room status
        required_fields = ['room_id', 'organizer_name', 'participant_count', 'approved_count', 'pending_count', 'total_polls', 'active_polls']
        for field in required_fields:
            if field not in response:
                self.log_test(f"Room Status Field: {field}", False, "Missing field")
                return False
        
        self.log_test("Room Status Fields Complete", True, "All required fields present")
        return True

    def test_participant_management(self):
        """Test 3: Participant Management"""
        print("\n🔍 Testing Participant Management")
        
        if not self.room_id:
            self.log_test("Participant Management", False, "No room ID available")
            return False
        
        # Test joining room
        participant_names = ["Alice Johnson", "Bob Smith", "Charlie Brown"]
        for name in participant_names:
            success, response = self.run_test(
                f"Join Room - {name}",
                "POST",
                "api/rooms/join",
                200,
                params={"room_id": self.room_id, "participant_name": name}
            )
            if not success:
                return False
            
            token = response.get('participant_token')
            if not token:
                self.log_test(f"Participant Token - {name}", False, "No token received")
                return False
            
            self.participant_tokens.append(token)
            
            # Verify approval status is pending
            if response.get('approval_status') != 'pending':
                self.log_test(f"Approval Status - {name}", False, f"Expected 'pending', got {response.get('approval_status')}")
                return False
        
        # Test joining invalid room
        success, response = self.run_test(
            "Join Invalid Room (Should Fail)",
            "POST",
            "api/rooms/join",
            404,
            params={"room_id": "INVALID123", "participant_name": "Invalid User"}
        )
        if not success:
            return False
        
        # Get participants list
        success, response = self.run_test(
            "Get Participants List",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        if not success:
            return False
        
        participants = response.get('participants', [])
        if len(participants) != 3:
            self.log_test("Participant Count", False, f"Expected 3, got {len(participants)}")
            return False
        
        # Store participant IDs and approve participants
        for p in participants:
            self.participant_ids.append(p['participant_id'])
            
            # Test approval
            success, response = self.run_test(
                f"Approve Participant - {p['participant_name']}",
                "POST",
                f"api/participants/{p['participant_id']}/approve",
                200
            )
            if not success:
                return False
        
        # Test denying a participant (create new one first)
        success, response = self.run_test(
            "Join Room for Deny Test",
            "POST",
            "api/rooms/join",
            200,
            params={"room_id": self.room_id, "participant_name": "Deny Test User"}
        )
        if not success:
            return False
        
        # Get updated participants list to find the new participant
        success, response = self.run_test(
            "Get Participants for Deny Test",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        if not success:
            return False
        
        deny_participant_id = None
        for p in response['participants']:
            if p['participant_name'] == "Deny Test User":
                deny_participant_id = p['participant_id']
                break
        
        if deny_participant_id:
            success, response = self.run_test(
                "Deny Participant",
                "POST",
                f"api/participants/{deny_participant_id}/deny",
                200
            )
            if not success:
                return False
        
        self.log_test("Participant Management Complete", True, f"{len(self.participant_tokens)} participants managed")
        return True

    def test_poll_creation_and_management(self):
        """Test 4: Poll Creation and Management"""
        print("\n🔍 Testing Poll Creation and Management")
        
        if not self.room_id:
            self.log_test("Poll Management", False, "No room ID available")
            return False
        
        # Test creating polls with different configurations
        poll_configs = [
            {
                "room_id": self.room_id,
                "question": "What is your favorite programming language?",
                "options": ["Python", "JavaScript", "Java", "Go"]
            },
            {
                "room_id": self.room_id,
                "question": "Which framework do you prefer?",
                "options": ["React", "Vue", "Angular"]
            },
            {
                "room_id": self.room_id,
                "question": "Timed poll - favorite color?",
                "options": ["Red", "Blue", "Green", "Yellow"],
                "timer_minutes": 5
            }
        ]
        
        for i, poll_data in enumerate(poll_configs):
            success, response = self.run_test(
                f"Create Poll {i+1}",
                "POST",
                "api/polls/create",
                200,
                data=poll_data
            )
            if not success:
                return False
            
            poll_id = response.get('poll_id')
            if not poll_id:
                self.log_test(f"Poll ID Assignment {i+1}", False, "No poll_id in response")
                return False
            
            self.poll_ids.append(poll_id)
        
        # Test getting all polls
        success, response = self.run_test(
            "Get All Polls",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        if not success:
            return False
        
        polls = response.get('polls', [])
        if len(polls) != 3:
            self.log_test("Poll Count", False, f"Expected 3, got {len(polls)}")
            return False
        
        # Verify poll structure
        for poll in polls:
            required_fields = ['poll_id', 'question', 'options', 'is_active', 'vote_counts', 'total_votes']
            for field in required_fields:
                if field not in poll:
                    self.log_test(f"Poll Structure - {field}", False, "Missing field")
                    return False
        
        self.log_test("Poll Creation Complete", True, f"{len(self.poll_ids)} polls created")
        return True

    def test_poll_lifecycle(self):
        """Test 5: Poll Lifecycle (Start/Stop/Restart)"""
        print("\n🔍 Testing Poll Lifecycle")
        
        if not self.poll_ids:
            self.log_test("Poll Lifecycle", False, "No poll IDs available")
            return False
        
        poll_id = self.poll_ids[0]
        
        # Test starting poll
        success, response = self.run_test(
            "Start Poll",
            "POST",
            f"api/polls/{poll_id}/start",
            200
        )
        if not success:
            return False
        
        # Verify poll is active
        success, response = self.run_test(
            "Verify Poll Active",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if not success:
            return False
        
        active_polls = response.get('active_polls', [])
        if not any(p['poll_id'] == poll_id for p in active_polls):
            self.log_test("Poll Active Verification", False, "Poll not found in active polls")
            return False
        
        # Test stopping poll
        success, response = self.run_test(
            "Stop Poll",
            "POST",
            f"api/polls/{poll_id}/stop",
            200
        )
        if not success:
            return False
        
        # Verify poll is stopped
        success, response = self.run_test(
            "Verify Poll Stopped",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if not success:
            return False
        
        active_polls = response.get('active_polls', [])
        if any(p['poll_id'] == poll_id for p in active_polls):
            self.log_test("Poll Stop Verification", False, "Poll still found in active polls")
            return False
        
        # Test restarting poll
        success, response = self.run_test(
            "Restart Poll",
            "POST",
            f"api/polls/{poll_id}/start",
            200
        )
        if not success:
            return False
        
        self.log_test("Poll Lifecycle Complete", True, "Start/Stop/Restart working")
        return True

    def test_voting_system(self):
        """Test 6: Voting System"""
        print("\n🔍 Testing Voting System")
        
        if not self.poll_ids or not self.participant_tokens:
            self.log_test("Voting System", False, "No polls or participants available")
            return False
        
        poll_id = self.poll_ids[0]
        
        # Test voting with approved participants
        options = ["Python", "JavaScript", "Java"]
        for i, (token, option) in enumerate(zip(self.participant_tokens, options)):
            vote_data = {
                "participant_token": token,
                "selected_option": option
            }
            
            success, response = self.run_test(
                f"Vote {i+1} - {option}",
                "POST",
                f"api/polls/{poll_id}/vote",
                200,
                data=vote_data
            )
            if not success:
                return False
        
        # Test duplicate vote (should fail)
        vote_data = {
            "participant_token": self.participant_tokens[0],
            "selected_option": "Go"
        }
        
        success, response = self.run_test(
            "Duplicate Vote (Should Fail)",
            "POST",
            f"api/polls/{poll_id}/vote",
            400,
            data=vote_data
        )
        if not success:
            return False
        
        # Test voting with invalid option
        vote_data = {
            "participant_token": self.participant_tokens[0],
            "selected_option": "InvalidOption"
        }
        
        success, response = self.run_test(
            "Invalid Option Vote (Should Fail)",
            "POST",
            f"api/polls/{poll_id}/vote",
            400,
            data=vote_data
        )
        if not success:
            return False
        
        # Test voting on inactive poll
        inactive_poll_id = self.poll_ids[1]  # This poll was never started
        vote_data = {
            "participant_token": self.participant_tokens[0],
            "selected_option": "React"
        }
        
        success, response = self.run_test(
            "Vote on Inactive Poll (Should Fail)",
            "POST",
            f"api/polls/{inactive_poll_id}/vote",
            404,
            data=vote_data
        )
        if not success:
            return False
        
        # Verify vote counts
        success, response = self.run_test(
            "Check Vote Results",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        if not success:
            return False
        
        polls = response.get('polls', [])
        for poll in polls:
            if poll['poll_id'] == poll_id:
                total_votes = poll.get('total_votes', 0)
                if total_votes != 3:
                    self.log_test("Vote Count Verification", False, f"Expected 3 votes, got {total_votes}")
                    return False
                break
        
        self.log_test("Voting System Complete", True, "All voting scenarios tested")
        return True

    def test_multiple_active_polls(self):
        """Test 7: Multiple Active Polls"""
        print("\n🔍 Testing Multiple Active Polls")
        
        if len(self.poll_ids) < 2:
            self.log_test("Multiple Active Polls", False, "Need at least 2 polls")
            return False
        
        # Start multiple polls
        for i, poll_id in enumerate(self.poll_ids[1:3]):  # Start polls 2 and 3
            success, response = self.run_test(
                f"Start Poll {i+2}",
                "POST",
                f"api/polls/{poll_id}/start",
                200
            )
            if not success:
                return False
        
        # Verify multiple active polls
        success, response = self.run_test(
            "Check Multiple Active Polls",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if not success:
            return False
        
        active_poll_count = response.get('active_poll_count', 0)
        if active_poll_count < 2:
            self.log_test("Multiple Active Polls Count", False, f"Expected at least 2, got {active_poll_count}")
            return False
        
        self.log_test("Multiple Active Polls Complete", True, f"{active_poll_count} polls active simultaneously")
        return True

    def test_pdf_report_generation(self):
        """Test 8: PDF Report Generation"""
        print("\n🔍 Testing PDF Report Generation")
        
        if not self.room_id:
            self.log_test("PDF Generation", False, "No room ID available")
            return False
        
        try:
            url = f"{self.base_url}/api/rooms/{self.room_id}/report"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("PDF Generation", False, f"Status: {response.status_code}")
                return False
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type:
                self.log_test("PDF Content Type", False, f"Expected PDF, got {content_type}")
                return False
            
            # Check content disposition
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'filename=' not in content_disposition:
                self.log_test("PDF Filename Header", False, "No filename in header")
                return False
            
            # Check PDF content
            if not response.content.startswith(b'%PDF'):
                self.log_test("PDF Content Validation", False, "Invalid PDF content")
                return False
            
            pdf_size = len(response.content)
            self.log_test("PDF Generation Complete", True, f"PDF size: {pdf_size} bytes")
            return True
            
        except Exception as e:
            self.log_test("PDF Generation", False, f"Exception: {str(e)}")
            return False

    def test_websocket_connectivity(self):
        """Test 9: WebSocket Connectivity"""
        print("\n🔍 Testing WebSocket Connectivity")
        
        if not self.room_id:
            self.log_test("WebSocket Test", False, "No room ID available")
            return False
        
        try:
            # Test WebSocket connection
            ws_url = f"wss://2c9a952d-eabb-4b15-8a17-009575d29e56.preview.emergentagent.com/api/ws/{self.room_id}"
            
            def on_message(ws, message):
                self.websocket_messages.append(message)
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                pass
            
            def on_open(ws):
                # Send a test message
                ws.send("test")
                # Close after a short delay
                threading.Timer(2.0, ws.close).start()
            
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run WebSocket in a separate thread with timeout
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            ws_thread.join(timeout=5)
            
            self.log_test("WebSocket Connectivity", True, "Connection established and closed successfully")
            return True
            
        except Exception as e:
            self.log_test("WebSocket Connectivity", False, f"Exception: {str(e)}")
            return False

    def test_data_cleanup(self):
        """Test 10: Data Cleanup"""
        print("\n🔍 Testing Data Cleanup")
        
        if not self.room_id:
            self.log_test("Data Cleanup", False, "No room ID available")
            return False
        
        success, response = self.run_test(
            "Cleanup Room Data",
            "DELETE",
            f"api/rooms/{self.room_id}/cleanup",
            200
        )
        if not success:
            return False
        
        # Verify room is deleted
        success, response = self.run_test(
            "Verify Room Deleted",
            "GET",
            f"api/rooms/{self.room_id}/status",
            404
        )
        if not success:
            return False
        
        self.log_test("Data Cleanup Complete", True, "Room and all associated data deleted")
        return True

    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Secret Poll Backend API Tests")
        print("🎯 Testing: All Major Endpoints and Functionality")
        print("=" * 80)
        
        test_functions = [
            self.test_health_check,
            self.test_room_creation_and_management,
            self.test_participant_management,
            self.test_poll_creation_and_management,
            self.test_poll_lifecycle,
            self.test_voting_system,
            self.test_multiple_active_polls,
            self.test_pdf_report_generation,
            self.test_websocket_connectivity,
            self.test_data_cleanup
        ]
        
        all_passed = True
        for test_func in test_functions:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                print(f"❌ Test {test_func.__name__} failed with exception: {e}")
                all_passed = False
        
        return all_passed

def main():
    """Main test function"""
    tester = ComprehensiveAPITester()
    
    success = tester.run_comprehensive_tests()
    
    # Print final results
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if success and tester.tests_passed == tester.tests_run:
        print("🎉 All comprehensive tests passed!")
        return 0
    else:
        print("❌ Some comprehensive tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())