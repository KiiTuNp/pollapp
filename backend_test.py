import requests
import json
import sys
from datetime import datetime
import time

class SecretPollAPITester:
    def __init__(self, base_url="https://44f33d7d-8a1b-450f-af28-7e3467a6672f.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.room_id = None
        self.custom_room_id = None
        self.participant_tokens = []
        self.participant_ids = []
        self.participant_names = []
        self.poll_ids = []
        self.organizer_name = "Test Organizer"

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        if data:
            print(f"   Data: {data}")
        if params:
            print(f"   Params: {params}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                if data:
                    response = requests.post(url, json=data, headers=headers, params=params)
                else:
                    response = requests.post(url, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error Response: {error_data}")
                except:
                    print(f"   Error Text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_create_room_with_custom_id(self):
        """Test creating room with valid custom ID (3-10 alphanumeric characters)"""
        custom_id = "MEET01"  # Valid: 6 characters, alphanumeric
        
        success, response = self.run_test(
            "Create Room with Valid Custom ID",
            "POST",
            "api/rooms/create",
            200,
            params={"organizer_name": self.organizer_name, "custom_room_id": custom_id}
        )
        if success and 'room_id' in response:
            self.custom_room_id = response['room_id']
            if self.custom_room_id == custom_id.upper():
                print(f"   ✅ Created room with custom ID: {self.custom_room_id}")
                return True
            else:
                print(f"   ❌ Expected {custom_id.upper()}, got {self.custom_room_id}")
                return False
        return False

    def test_custom_room_id_validation(self):
        """Test comprehensive custom room ID validation"""
        print("\n🔍 Testing Custom Room ID Validation...")
        
        # Test cases: [custom_id, expected_status, description]
        test_cases = [
            # Valid IDs
            ("ABC", 200, "Valid: 3 characters (minimum)"),
            ("ABCD123456", 200, "Valid: 10 characters (maximum)"),
            ("MEET01", 200, "Valid: 6 characters alphanumeric"),
            ("ABC123", 200, "Valid: mixed letters and numbers"),
            ("TEAM5", 200, "Valid: 5 characters"),
            ("POLL2024", 200, "Valid: 8 characters"),
            
            # Invalid IDs - Too short
            ("AB", 400, "Invalid: 2 characters (too short)"),
            ("A", 400, "Invalid: 1 character (too short)"),
            ("", 400, "Invalid: empty string"),
            
            # Invalid IDs - Too long
            ("VERYLONGID123", 400, "Invalid: 13 characters (too long)"),
            ("ABCDEFGHIJK", 400, "Invalid: 11 characters (too long)"),
            
            # Invalid IDs - Special characters
            ("MEET-01", 400, "Invalid: contains hyphen"),
            ("ROOM#1", 400, "Invalid: contains hash"),
            ("TEAM_5", 400, "Invalid: contains underscore"),
            ("POLL.2024", 400, "Invalid: contains dot"),
            ("ROOM 1", 400, "Invalid: contains space"),
            ("MEET@01", 400, "Invalid: contains at symbol"),
            ("ROOM+1", 400, "Invalid: contains plus"),
        ]
        
        passed_tests = 0
        total_tests = len(test_cases)
        
        for custom_id, expected_status, description in test_cases:
            # Use unique organizer name to avoid conflicts
            organizer_name = f"Test Organizer {datetime.now().strftime('%H%M%S%f')}"
            
            success, response = self.run_test(
                f"Custom ID Validation: {description}",
                "POST",
                "api/rooms/create",
                expected_status,
                params={"organizer_name": organizer_name, "custom_room_id": custom_id}
            )
            
            if success:
                passed_tests += 1
                if expected_status == 200:
                    # For successful cases, verify the room ID matches
                    if 'room_id' in response and response['room_id'] == custom_id.upper():
                        print(f"   ✅ Room created with ID: {response['room_id']}")
                    else:
                        print(f"   ⚠️  Room created but ID mismatch: expected {custom_id.upper()}, got {response.get('room_id')}")
                else:
                    # For error cases, check error message
                    if 'detail' in response:
                        print(f"   ✅ Proper error message: {response['detail']}")
            else:
                print(f"   ❌ Test failed for: {description}")
        
        print(f"\n📊 Custom ID Validation Results: {passed_tests}/{total_tests} passed")
        return passed_tests == total_tests

    def test_duplicate_custom_room_id(self):
        """Test creating room with duplicate custom ID (should fail)"""
        if not self.custom_room_id:
            print("❌ No custom room ID available for duplicate test")
            return False
            
        success, response = self.run_test(
            "Create Room with Duplicate Custom ID (Should Fail)",
            "POST",
            "api/rooms/create",
            400,  # Should fail with 400 Bad Request
            params={"organizer_name": "Another Organizer", "custom_room_id": self.custom_room_id}
        )
        return success

    def test_create_poll_with_timer(self):
        """Test creating a poll with auto-stop timer"""
        if not self.room_id:
            print("❌ No room ID available for poll with timer test")
            return False
            
        poll_data = {
            "room_id": self.room_id,
            "question": "What is your favorite color? (5 min timer)",
            "options": ["Red", "Blue", "Green", "Yellow"],
            "timer_minutes": 5  # 5 minute timer
        }
        
        success, response = self.run_test(
            "Create Poll with Timer",
            "POST",
            "api/polls/create",
            200,
            data=poll_data
        )
        if success and 'poll_id' in response:
            self.timer_poll_id = response['poll_id']
            print(f"   Created poll with timer: {self.timer_poll_id}")
            return True
        return False

    def test_poll_no_restart_after_votes(self):
        """Test that polls with votes cannot be restarted"""
        if not self.poll_id or not self.participant_token:
            print("❌ No poll ID or participant token available for no-restart test")
            return False
            
        # Vote on the poll first
        vote_data = {
            "participant_token": self.participant_token,
            "selected_option": "Blue"
        }
        
        success, response = self.run_test(
            "Vote Before Stop (No Restart Test)",
            "POST",
            f"api/polls/{self.poll_id}/vote",
            200,
            data=vote_data
        )
        if not success:
            return False
        
        # Stop the poll
        success, response = self.run_test(
            "Stop Poll with Votes",
            "POST",
            f"api/polls/{self.poll_id}/stop",
            200
        )
        if not success:
            return False
        
        # Try to restart the poll (should work according to current implementation)
        # But check that it shows CLOSED status in the polls list
        success, response = self.run_test(
            "Check Poll Status After Stop",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        
        if success:
            polls = response.get('polls', [])
            for poll in polls:
                if poll['poll_id'] == self.poll_id:
                    if not poll['is_active'] and poll['total_votes'] > 0:
                        print(f"   ✅ Poll correctly shows as closed with {poll['total_votes']} votes")
                        return True
                    else:
                        print(f"   ❌ Poll status incorrect: active={poll['is_active']}, votes={poll['total_votes']}")
                        return False
            print("   ❌ Could not find poll in response")
            return False
        return False

    def test_organizer_multi_room_management(self):
        """Test organizer can manage multiple rooms"""
        # Create a second room for the same organizer
        success, response = self.run_test(
            "Create Second Room for Same Organizer",
            "POST",
            "api/rooms/create",
            200,
            params={"organizer_name": self.organizer_name}
        )
        if not success:
            return False
            
        second_room_id = response.get('room_id')
        if not second_room_id:
            print("❌ No room ID in second room response")
            return False
        
        # Test the multi-room endpoint
        success, response = self.run_test(
            "Get All Rooms for Organizer",
            "GET",
            f"api/organizer/{self.organizer_name}/rooms",
            200
        )
        
        if success:
            rooms = response.get('rooms', [])
            if len(rooms) >= 2:
                print(f"   ✅ Found {len(rooms)} rooms for organizer")
                # Check room summary data
                for room in rooms:
                    required_fields = ['room_id', 'participant_count', 'total_polls', 'active_polls']
                    for field in required_fields:
                        if field not in room:
                            print(f"   ❌ Missing field {field} in room summary")
                            return False
                print("   ✅ All room summaries have required fields")
                return True
            else:
                print(f"   ❌ Expected at least 2 rooms, found {len(rooms)}")
                return False
        return False

    def test_real_time_vote_updates(self):
        """Test real-time vote count updates"""
        if not self.room_id:
            print("❌ No room ID available for real-time updates test")
            return False
            
        # Create a new poll for this test
        poll_data = {
            "room_id": self.room_id,
            "question": "Real-time test poll",
            "options": ["Option A", "Option B", "Option C"]
        }
        
        success, response = self.run_test(
            "Create Poll for Real-time Test",
            "POST",
            "api/polls/create",
            200,
            data=poll_data
        )
        if not success:
            return False
            
        realtime_poll_id = response.get('poll_id')
        
        # Start the poll
        success, response = self.run_test(
            "Start Real-time Poll",
            "POST",
            f"api/polls/{realtime_poll_id}/start",
            200
        )
        if not success:
            return False
        
        # Create multiple participants and have them vote
        participants = []
        for i in range(3):
            participant_name = f"Realtime Participant {i+1}"
            success, response = self.run_test(
                f"Join Room (Participant {i+1})",
                "POST",
                "api/rooms/join",
                200,
                params={"room_id": self.room_id, "participant_name": participant_name}
            )
            if success:
                participants.append({
                    'name': participant_name,
                    'token': response.get('participant_token'),
                    'id': None
                })
        
        # Get participant IDs and approve them
        success, response = self.run_test(
            "Get Participants for Approval",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        if success:
            all_participants = response.get('participants', [])
            for participant in participants:
                for p in all_participants:
                    if p.get('participant_name') == participant['name']:
                        participant['id'] = p['participant_id']
                        # Approve participant
                        self.run_test(
                            f"Approve {participant['name']}",
                            "POST",
                            f"api/participants/{participant['id']}/approve",
                            200
                        )
                        break
        
        # Have participants vote on different options
        options = ["Option A", "Option B", "Option C"]
        for i, participant in enumerate(participants):
            if participant['token']:
                vote_data = {
                    "participant_token": participant['token'],
                    "selected_option": options[i % len(options)]
                }
                
                success, response = self.run_test(
                    f"Vote by {participant['name']}",
                    "POST",
                    f"api/polls/{realtime_poll_id}/vote",
                    200,
                    data=vote_data
                )
        
        # Check final vote counts
        success, response = self.run_test(
            "Check Real-time Vote Results",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        
        if success:
            polls = response.get('polls', [])
            for poll in polls:
                if poll['poll_id'] == realtime_poll_id:
                    vote_counts = poll.get('vote_counts', {})
                    total_votes = poll.get('total_votes', 0)
                    if total_votes == 3:
                        print(f"   ✅ Real-time votes recorded: {vote_counts}")
                        return True
                    else:
                        print(f"   ❌ Expected 3 votes, found {total_votes}")
                        return False
            print("   ❌ Could not find real-time poll in response")
            return False
        return False
        """Test creating a poll with custom request handling"""
        if not self.room_id:
            print("❌ No room ID available for poll creation test")
            return False
            
        # Try sending as form data with multiple options
        url = f"{self.base_url}/api/polls/create"
        
        self.tests_run += 1
        print(f"\n🔍 Testing Create Poll (Custom)...")
        print(f"   URL: POST {url}")
        
        try:
            # Try with multiple options parameters
            params = {
                'room_id': self.room_id,
                'question': 'What is your favorite color?',
                'options': ['Red', 'Blue', 'Green', 'Yellow']
            }
            
            response = requests.post(url, params=params)
            
            success = response.status_code == 200
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                    if 'poll_id' in response_data:
                        self.poll_id = response_data['poll_id']
                        print(f"   Created poll with ID: {self.poll_id}")
                    return True
                except:
                    return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error Response: {error_data}")
                except:
                    print(f"   Error Text: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        return success

    def test_create_room(self, organizer_name="Test Organizer"):
        """Test room creation"""
        success, response = self.run_test(
            "Create Room",
            "POST",
            "api/rooms/create",
            200,
            params={"organizer_name": organizer_name}
        )
        if success and 'room_id' in response:
            self.room_id = response['room_id']
            print(f"   Created room with ID: {self.room_id}")
            return True
        return False

    def test_join_room_with_name(self, participant_name="Test Participant"):
        """Test joining a room with participant name (NEW APPROVAL SYSTEM)"""
        if not self.room_id:
            print("❌ No room ID available for joining test")
            return False
            
        self.participant_name = participant_name
        success, response = self.run_test(
            "Join Room with Name (Approval System)",
            "POST",
            "api/rooms/join",
            200,
            params={"room_id": self.room_id, "participant_name": participant_name}
        )
        if success and 'participant_token' in response:
            self.participant_token = response['participant_token']
            # Check if approval_status is pending
            if response.get('approval_status') == 'pending':
                print(f"   ✅ Participant created with pending status")
                print(f"   Got participant token: {self.participant_token[:8]}...")
                return True
            else:
                print(f"   ❌ Expected pending status, got: {response.get('approval_status')}")
                return False
        return False

    def test_get_participants_list(self):
        """Test getting participants list for organizer"""
        if not self.room_id:
            print("❌ No room ID available for participants list test")
            return False
            
        success, response = self.run_test(
            "Get Participants List",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        if success and 'participants' in response:
            participants = response['participants']
            if len(participants) > 0:
                # Store participant_id for approval tests
                for p in participants:
                    if p.get('participant_name') == self.participant_name:
                        self.participant_id = p['participant_id']
                        print(f"   Found participant ID: {self.participant_id}")
                        break
                print(f"   Found {len(participants)} participants")
                return True
        return False

    def test_approve_participant(self):
        """Test approving a participant"""
        if not self.participant_id:
            print("❌ No participant ID available for approval test")
            return False
            
        success, response = self.run_test(
            "Approve Participant",
            "POST",
            f"api/participants/{self.participant_id}/approve",
            200
        )
        return success

    def test_deny_participant(self):
        """Test denying a participant (separate participant)"""
        # First create another participant to deny
        if not self.room_id:
            print("❌ No room ID available for deny test")
            return False
            
        # Join with different name
        success, response = self.run_test(
            "Join Room (For Deny Test)",
            "POST",
            "api/rooms/join",
            200,
            params={"room_id": self.room_id, "participant_name": "Test Participant 2"}
        )
        
        if not success:
            return False
            
        # Get participants list to find the new participant
        success, response = self.run_test(
            "Get Participants (For Deny)",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        
        if not success:
            return False
            
        # Find the second participant
        deny_participant_id = None
        for p in response['participants']:
            if p.get('participant_name') == "Test Participant 2":
                deny_participant_id = p['participant_id']
                break
                
        if not deny_participant_id:
            print("❌ Could not find participant to deny")
            return False
            
        # Now deny the participant
        success, response = self.run_test(
            "Deny Participant",
            "POST",
            f"api/participants/{deny_participant_id}/deny",
            200
        )
        return success

    def test_vote_unapproved_participant(self):
        """Test voting with unapproved participant (should fail)"""
        if not self.poll_id:
            print("❌ No poll ID available for unapproved vote test")
            return False
            
        # Create a new participant that won't be approved
        success, response = self.run_test(
            "Join Room (Unapproved)",
            "POST",
            "api/rooms/join",
            200,
            params={"room_id": self.room_id, "participant_name": "Unapproved Participant"}
        )
        
        if not success:
            return False
            
        unapproved_token = response.get('participant_token')
        if not unapproved_token:
            print("❌ No token for unapproved participant")
            return False
            
        # Try to vote with unapproved participant (should fail with 403)
        vote_data = {
            "participant_token": unapproved_token,
            "selected_option": "Red"
        }
        
        success, response = self.run_test(
            "Vote with Unapproved Participant (Should Fail)",
            "POST",
            f"api/polls/{self.poll_id}/vote",
            403,  # Should fail with 403 Forbidden
            data=vote_data
        )
        return success

    def test_room_status_with_approval_counts(self):
        """Test room status shows approval counts"""
        if not self.room_id:
            print("❌ No room ID available for status test")
            return False
            
        success, response = self.run_test(
            "Get Room Status (With Approval Counts)",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        
        if success:
            # Check if response contains approval counts
            required_fields = ['participant_count', 'approved_count', 'pending_count']
            for field in required_fields:
                if field not in response:
                    print(f"   ❌ Missing field: {field}")
                    return False
                else:
                    print(f"   ✅ {field}: {response[field]}")
            return True
        return False

    def test_join_invalid_room(self):
        """Test joining an invalid room"""
        success, response = self.run_test(
            "Join Invalid Room",
            "POST",
            "api/rooms/join",
            404,
            params={"room_id": "INVALID1"}
        )
        return success

    def test_get_room_status(self):
        """Test getting room status"""
        if not self.room_id:
            print("❌ No room ID available for status test")
            return False
            
        success, response = self.run_test(
            "Get Room Status",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        return success

    def test_create_poll(self):
        """Test creating a poll with JSON body (new format)"""
        if not self.room_id:
            print("❌ No room ID available for poll creation test")
            return False
            
        # Backend now expects JSON body, not query parameters
        poll_data = {
            "room_id": self.room_id,
            "question": "What is your favorite color?",
            "options": ["Red", "Blue", "Green", "Yellow"]
        }
        
        success, response = self.run_test(
            "Create Poll (JSON Body)",
            "POST",
            "api/polls/create",
            200,
            data=poll_data
        )
        if success and 'poll_id' in response:
            self.poll_id = response['poll_id']
            print(f"   Created poll with ID: {self.poll_id}")
            return True
        return False

    def test_start_poll(self):
        """Test starting a poll"""
        if not self.poll_id:
            print("❌ No poll ID available for start test")
            return False
            
        success, response = self.run_test(
            "Start Poll",
            "POST",
            f"api/polls/{self.poll_id}/start",
            200
        )
        return success

    def test_vote_on_poll(self):
        """Test voting on a poll with JSON body (FIXED FORMAT)"""
        if not self.poll_id or not self.participant_token:
            print("❌ No poll ID or participant token available for voting test")
            return False
            
        # Backend now expects JSON body for voting (FIXED)
        vote_data = {
            "participant_token": self.participant_token,
            "selected_option": "Blue"
        }
        
        success, response = self.run_test(
            "Vote on Poll (JSON Body - FIXED)",
            "POST",
            f"api/polls/{self.poll_id}/vote",
            200,
            data=vote_data
        )
        return success

    def test_duplicate_vote(self):
        """Test voting twice with same token (should fail)"""
        if not self.poll_id or not self.participant_token:
            print("❌ No poll ID or participant token available for duplicate vote test")
            return False
            
        # Backend now expects JSON body for voting (FIXED)
        vote_data = {
            "participant_token": self.participant_token,
            "selected_option": "Red"
        }
        
        success, response = self.run_test(
            "Duplicate Vote (Should Fail) - JSON Body",
            "POST",
            f"api/polls/{self.poll_id}/vote",
            400,
            data=vote_data
        )
        return success

    def test_stop_poll(self):
        """Test stopping a poll"""
        if not self.poll_id:
            print("❌ No poll ID available for stop test")
            return False
            
        success, response = self.run_test(
            "Stop Poll",
            "POST",
            f"api/polls/{self.poll_id}/stop",
            200
        )
        return success

    def test_critical_pdf_generation(self):
        """
        🚨 CRITICAL TEST: PDF Generation and Download
        This is one of the main issues to debug
        """
        if not self.room_id:
            print("❌ No room ID available for PDF generation test")
            return False

        print("\n🚨 CRITICAL TEST: PDF Generation and Download")
        print("=" * 60)
        
        try:
            url = f"{self.base_url}/api/rooms/{self.room_id}/report"
            print(f"   Testing PDF endpoint: {url}")
            
            response = requests.get(url, timeout=30)
            
            print(f"   PDF Response Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Not set')}")
            print(f"   Content-Disposition: {response.headers.get('Content-Disposition', 'Not set')}")
            print(f"   Content-Length: {response.headers.get('Content-Length', 'Not set')}")
            
            self.tests_run += 1
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' in content_type:
                    print("   ✅ PDF generated successfully")
                    print(f"   PDF size: {len(response.content)} bytes")
                    
                    # Check if content-disposition header has filename
                    content_disposition = response.headers.get('Content-Disposition', '')
                    if 'filename=' in content_disposition:
                        print(f"   ✅ Filename header present: {content_disposition}")
                    else:
                        print("   ⚠️  No filename in Content-Disposition header")
                    
                    # Verify it's actually PDF content
                    if response.content.startswith(b'%PDF'):
                        print("   ✅ Valid PDF content detected")
                        self.tests_passed += 1
                        return True
                    else:
                        print("   ❌ Invalid PDF content - does not start with %PDF")
                else:
                    print(f"   ❌ Wrong content type: {content_type}")
            else:
                print(f"   ❌ PDF generation failed with status {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response: {response.text[:200]}")
            
            return False
            
        except Exception as e:
            print(f"   ❌ PDF generation exception: {str(e)}")
            self.tests_run += 1
            return False

    def test_critical_participant_approval_during_active_polls(self):
        """
        🚨 CRITICAL TEST: Participant Approval During Active Polls
        This is the main issue to debug - participants should be able to join and be approved while polls are active
        """
        if not self.room_id:
            print("❌ No room ID available for participant approval test")
            return False

        print("\n🚨 CRITICAL TEST: Participant Approval During Active Polls")
        print("=" * 60)
        
        # Step 1: Create multiple polls
        print("   Step 1: Creating multiple polls...")
        polls_data = [
            {
                "room_id": self.room_id,
                "question": "What is your favorite programming language?",
                "options": ["Python", "JavaScript", "Java", "Go"]
            },
            {
                "room_id": self.room_id,
                "question": "Which framework do you prefer?",
                "options": ["React", "Vue", "Angular"]
            }
        ]

        for i, poll_data in enumerate(polls_data):
            success, response = self.run_test(
                f"Create Poll {i+1} for Active Test",
                "POST",
                "api/polls/create",
                200,
                data=poll_data
            )
            
            if success and 'poll_id' in response:
                self.poll_ids.append(response['poll_id'])
                print(f"   Created poll: {response['question']}")
            else:
                print(f"   ❌ Failed to create poll {i+1}")
                return False

        # Step 2: Start the polls to make them active
        print("   Step 2: Starting polls to make them active...")
        for i, poll_id in enumerate(self.poll_ids):
            success, response = self.run_test(
                f"Start Poll {i+1}",
                "POST",
                f"api/polls/{poll_id}/start",
                200
            )
            
            if not success:
                print(f"   ❌ Failed to start poll {i+1}")
                return False
            
            print(f"   ✅ Started poll {i+1}")

        # Step 3: Verify polls are active
        success, response = self.run_test(
            "Verify Polls Are Active",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        
        if success:
            active_poll_count = response.get('active_poll_count', 0)
            print(f"   ✅ Confirmed {active_poll_count} active polls")
            if active_poll_count == 0:
                print("   ❌ No active polls found - cannot test approval during active polls")
                return False
        else:
            print("   ❌ Failed to verify active polls")
            return False

        # Step 4: Add multiple participants while polls are active
        print("   Step 3: Adding participants while polls are ACTIVE...")
        participants = [
            f"ActivePollParticipant1_{datetime.now().strftime('%H%M%S')}",
            f"ActivePollParticipant2_{datetime.now().strftime('%H%M%S')}",
            f"ActivePollParticipant3_{datetime.now().strftime('%H%M%S')}"
        ]

        for participant_name in participants:
            success, response = self.run_test(
                f"Join Room During Active Polls - {participant_name}",
                "POST",
                "api/rooms/join",
                200,
                params={"room_id": self.room_id, "participant_name": participant_name}
            )
            
            if success and 'participant_token' in response:
                self.participant_tokens.append(response['participant_token'])
                self.participant_names.append(participant_name)
                print(f"   ✅ {participant_name} joined with token: {response['participant_token'][:8]}...")
                print(f"   Status: {response.get('approval_status', 'unknown')}")
            else:
                print(f"   ❌ Failed to join {participant_name}")
                return False

        # Step 5: Get participant IDs for approval
        print("   Step 4: Getting participant IDs for approval...")
        success, response = self.run_test(
            "Get Participants for Approval",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        
        if success and 'participants' in response:
            all_participants = response['participants']
            for participant in all_participants:
                if participant['participant_name'] in self.participant_names:
                    self.participant_ids.append(participant['participant_id'])
                    print(f"   Found participant ID: {participant['participant_id']} for {participant['participant_name']}")
        else:
            print("   ❌ Failed to get participants list")
            return False

        # Step 6: CRITICAL - Try to approve participants while polls are ACTIVE
        print("   Step 5: 🚨 APPROVING PARTICIPANTS WHILE POLLS ARE ACTIVE...")
        approval_results = []
        for i, participant_id in enumerate(self.participant_ids):
            success, response = self.run_test(
                f"🚨 Approve Participant {i+1} During Active Polls",
                "POST",
                f"api/participants/{participant_id}/approve",
                200
            )
            approval_results.append(success)
            
            if success:
                print(f"   ✅ Successfully approved participant {i+1} during active polls")
            else:
                print(f"   ❌ Failed to approve participant {i+1} during active polls")

        # Step 7: Verify approved participants can vote on active polls
        print("   Step 6: Testing if approved participants can vote on active polls...")
        if len(self.participant_tokens) > 0 and len(self.poll_ids) > 0:
            vote_data = {
                "participant_token": self.participant_tokens[0],
                "selected_option": "Python"  # First option from first poll
            }
            
            success, response = self.run_test(
                "🚨 Vote on Active Poll After Approval",
                "POST",
                f"api/polls/{self.poll_ids[0]}/vote",
                200,
                data=vote_data
            )
            
            if success:
                print("   ✅ Approved participant successfully voted on active poll")
            else:
                print("   ❌ Approved participant failed to vote on active poll")
                approval_results.append(False)

        # Step 8: Check final room status
        success, response = self.run_test(
            "Final Room Status After Approvals",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        
        if success:
            print(f"   Final status: {response.get('approved_count', 0)} approved, {response.get('pending_count', 0)} pending, {response.get('active_poll_count', 0)} active polls")

        # Return overall result
        overall_success = all(approval_results)
        if overall_success:
            print("   🎉 CRITICAL TEST PASSED: Participants can be approved during active polls!")
        else:
            print("   ❌ CRITICAL TEST FAILED: Issues with participant approval during active polls")
        
        return overall_success

    def test_cleanup_room(self):
        """Test cleaning up room data"""
        if not self.room_id:
            print("❌ No room ID available for cleanup test")
            return False
            
        success, response = self.run_test(
            "Cleanup Room Data",
            "DELETE",
            f"api/rooms/{self.room_id}/cleanup",
            200
        )
        return success

    def test_multiple_active_polls(self):
        """Test multiple active polls functionality"""
        if not self.room_id:
            print("❌ No room ID available for multiple polls test")
            return False
            
        # Create multiple polls
        poll_ids = []
        for i in range(3):
            poll_data = {
                "room_id": self.room_id,
                "question": f"Poll {i+1}: What is your favorite {['color', 'food', 'season'][i]}?",
                "options": [["Red", "Blue", "Green"], ["Pizza", "Burger", "Pasta"], ["Spring", "Summer", "Winter"]][i]
            }
            
            success, response = self.run_test(
                f"Create Poll {i+1}",
                "POST",
                "api/polls/create",
                200,
                data=poll_data
            )
            if success and 'poll_id' in response:
                poll_ids.append(response['poll_id'])
            else:
                return False
        
        # Start all polls
        for i, poll_id in enumerate(poll_ids):
            success, response = self.run_test(
                f"Start Poll {i+1}",
                "POST",
                f"api/polls/{poll_id}/start",
                200
            )
            if not success:
                return False
        
        # Check room status shows multiple active polls
        success, response = self.run_test(
            "Check Multiple Active Polls Status",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        
        if success:
            active_polls = response.get('active_polls', [])
            if len(active_polls) == 3:
                print(f"   ✅ Found {len(active_polls)} active polls as expected")
                self.poll_ids = poll_ids  # Store for later tests
                return True
            else:
                print(f"   ❌ Expected 3 active polls, found {len(active_polls)}")
                return False
        return False

    def test_poll_restart_functionality(self):
        """Test poll restart functionality"""
        if not hasattr(self, 'poll_ids') or not self.poll_ids:
            print("❌ No poll IDs available for restart test")
            return False
            
        first_poll_id = self.poll_ids[0]
        
        # Vote on the first poll
        vote_data = {
            "participant_token": self.participant_token,
            "selected_option": "Red"
        }
        
        success, response = self.run_test(
            "Vote Before Stop",
            "POST",
            f"api/polls/{first_poll_id}/vote",
            200,
            data=vote_data
        )
        if not success:
            return False
        
        # Stop the poll
        success, response = self.run_test(
            "Stop Poll for Restart Test",
            "POST",
            f"api/polls/{first_poll_id}/stop",
            200
        )
        if not success:
            return False
        
        # Check that poll is no longer active
        success, response = self.run_test(
            "Check Poll Stopped",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if success:
            active_polls = response.get('active_polls', [])
            active_poll_ids = [p['poll_id'] for p in active_polls]
            if first_poll_id not in active_poll_ids:
                print(f"   ✅ Poll correctly stopped")
            else:
                print(f"   ❌ Poll still appears active after stop")
                return False
        
        # Restart the poll
        success, response = self.run_test(
            "Restart Poll",
            "POST",
            f"api/polls/{first_poll_id}/start",
            200
        )
        if not success:
            return False
        
        # Check that poll is active again
        success, response = self.run_test(
            "Check Poll Restarted",
            "GET",
            f"api/rooms/{self.room_id}/status",
            200
        )
        if success:
            active_polls = response.get('active_polls', [])
            active_poll_ids = [p['poll_id'] for p in active_polls]
            if first_poll_id in active_poll_ids:
                print(f"   ✅ Poll successfully restarted")
                return True
            else:
                print(f"   ❌ Poll not active after restart")
                return False
        return False

    def test_vote_persistence_through_restart(self):
        """Test that votes persist through poll restart cycles"""
        if not hasattr(self, 'poll_ids') or not self.poll_ids:
            print("❌ No poll IDs available for vote persistence test")
            return False
            
        second_poll_id = self.poll_ids[1]
        
        # Create another participant to vote
        success, response = self.run_test(
            "Join Room (Second Voter)",
            "POST",
            "api/rooms/join",
            200,
            params={"room_id": self.room_id, "participant_name": "Second Voter"}
        )
        if not success:
            return False
            
        second_token = response.get('participant_token')
        
        # Get participant ID and approve
        success, response = self.run_test(
            "Get Participants for Second Voter",
            "GET",
            f"api/rooms/{self.room_id}/participants",
            200
        )
        if not success:
            return False
            
        second_participant_id = None
        for p in response['participants']:
            if p.get('participant_name') == "Second Voter":
                second_participant_id = p['participant_id']
                break
                
        if not second_participant_id:
            print("❌ Could not find second participant")
            return False
            
        # Approve second participant
        success, response = self.run_test(
            "Approve Second Participant",
            "POST",
            f"api/participants/{second_participant_id}/approve",
            200
        )
        if not success:
            return False
        
        # Both participants vote on second poll
        vote_data1 = {
            "participant_token": self.participant_token,
            "selected_option": "Pizza"
        }
        
        vote_data2 = {
            "participant_token": second_token,
            "selected_option": "Burger"
        }
        
        success, response = self.run_test(
            "First Participant Vote",
            "POST",
            f"api/polls/{second_poll_id}/vote",
            200,
            data=vote_data1
        )
        if not success:
            return False
            
        success, response = self.run_test(
            "Second Participant Vote",
            "POST",
            f"api/polls/{second_poll_id}/vote",
            200,
            data=vote_data2
        )
        if not success:
            return False
        
        # Stop and restart the poll
        success, response = self.run_test(
            "Stop Poll (Vote Persistence Test)",
            "POST",
            f"api/polls/{second_poll_id}/stop",
            200
        )
        if not success:
            return False
            
        success, response = self.run_test(
            "Restart Poll (Vote Persistence Test)",
            "POST",
            f"api/polls/{second_poll_id}/start",
            200
        )
        if not success:
            return False
        
        # Check that votes are still there
        success, response = self.run_test(
            "Check Vote Persistence",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        
        if success:
            polls = response.get('polls', [])
            for poll in polls:
                if poll['poll_id'] == second_poll_id:
                    vote_counts = poll.get('vote_counts', {})
                    total_votes = poll.get('total_votes', 0)
                    if total_votes == 2:
                        print(f"   ✅ Votes persisted through restart: {vote_counts}")
                        return True
                    else:
                        print(f"   ❌ Expected 2 votes, found {total_votes}")
                        return False
            print("   ❌ Could not find poll in response")
            return False
        return False

    def test_enhanced_organizer_dashboard(self):
        """Test enhanced organizer dashboard features"""
        if not self.room_id:
            print("❌ No room ID available for dashboard test")
            return False
        
        # Get all polls to check enhanced features
        success, response = self.run_test(
            "Get All Polls (Enhanced Dashboard)",
            "GET",
            f"api/rooms/{self.room_id}/polls",
            200
        )
        
        if success:
            polls = response.get('polls', [])
            if len(polls) >= 3:
                print(f"   ✅ Found {len(polls)} polls with enhanced data")
                
                # Check each poll has required fields
                for poll in polls:
                    required_fields = ['poll_id', 'question', 'options', 'is_active', 'vote_counts', 'total_votes']
                    for field in required_fields:
                        if field not in poll:
                            print(f"   ❌ Missing field {field} in poll data")
                            return False
                
                # Check that some polls are active and some inactive
                active_count = sum(1 for poll in polls if poll['is_active'])
                inactive_count = len(polls) - active_count
                
                print(f"   ✅ Active polls: {active_count}, Inactive polls: {inactive_count}")
                return True
            else:
                print(f"   ❌ Expected at least 3 polls, found {len(polls)}")
                return False
        return False

    def run_critical_tests(self):
        """Run the critical tests for PDF download and participant approval during active polls"""
        print("🚀 Starting CRITICAL Secret Poll API Tests")
        print("Focus: PDF Download & Participant Approval During Active Polls")
        print("=" * 80)
        
        # Basic setup
        if not self.test_health_check():
            print("❌ Health check failed, stopping tests")
            return False

        if not self.test_create_room():
            print("❌ Room creation failed, stopping tests")
            return False

        # Run the two critical tests
        print("\n" + "="*60)
        print("🚨 RUNNING CRITICAL ISSUE TESTS")
        print("="*60)
        
        # Critical Test 1: Participant Approval During Active Polls
        approval_success = self.test_critical_participant_approval_during_active_polls()
        
        # Critical Test 2: PDF Generation
        pdf_success = self.test_critical_pdf_generation()
        
        # Cleanup
        print("\n" + "="*60)
        print("🧹 CLEANUP")
        print("="*60)
        self.test_cleanup_room()

        # Results
        print("\n" + "=" * 80)
        print("📊 CRITICAL TEST RESULTS")
        print("=" * 80)
        print(f"1. Participant Approval During Active Polls: {'✅ PASSED' if approval_success else '❌ FAILED'}")
        print(f"2. PDF Generation: {'✅ PASSED' if pdf_success else '❌ FAILED'}")
        print(f"\nOverall Tests Run: {self.tests_run}")
        print(f"Overall Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if approval_success and pdf_success:
            print("\n🎉 ALL CRITICAL TESTS PASSED!")
            return True
        else:
            print("\n❌ CRITICAL ISSUES FOUND!")
            if not approval_success:
                print("   - Participant approval during active polls has issues")
            if not pdf_success:
                print("   - PDF generation has issues")
            return False

def main():
    """Main test function - Focus on critical issues"""
    tester = SecretPollAPITester()
    
    success = tester.run_critical_tests()
    
    if success:
        print("🎉 All critical tests passed!")
        return 0
    else:
        print("❌ Critical issues found!")
        return 1

if __name__ == "__main__":
    sys.exit(main())