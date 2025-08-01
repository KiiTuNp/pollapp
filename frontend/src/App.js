import React, { useState, useEffect } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [roomData, setRoomData] = useState(null);
  const [participantToken, setParticipantToken] = useState(null);
  const [ws, setWs] = useState(null);
  const [activePolls, setActivePolls] = useState([]); // Changed from single activePoll to multiple activePolls
  const [allPolls, setAllPolls] = useState([]); // Track all polls with their statuses
  const [hasVoted, setHasVoted] = useState({});  // Changed to object to track votes per poll
  const [voteResults, setVoteResults] = useState({});
  const [pollTimers, setPollTimers] = useState({}); // Track timers for active polls
  const [roomStatus, setRoomStatus] = useState(null);
  const [createdPolls, setCreatedPolls] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [approvalStatus, setApprovalStatus] = useState(null);

  // Enhanced WebSocket with reconnection logic
  useEffect(() => {
    if (roomData && roomData.room_id) {
      let websocket;
      let reconnectAttempts = 0;
      const maxReconnectAttempts = 5;
      
      const connectWebSocket = () => {
        try {
          const wsUrl = `${BACKEND_URL.replace('http', 'ws')}/api/ws/${roomData.room_id}`;
          websocket = new WebSocket(wsUrl);
          
          websocket.onopen = () => {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
          };
          
          websocket.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              
              switch (data.type) {
                case 'participant_update':
                  if (roomStatus) {
                    setRoomStatus(prev => ({
                      ...prev,
                      participant_count: data.participant_count
                    }));
                  }
                  break;
                case 'poll_started':
                  const newPoll = {
                    poll_id: data.poll_id,
                    question: data.question,
                    options: data.options,
                    timer_minutes: data.timer_minutes
                  };
                  setActivePolls(prev => [...prev, newPoll]);
                  setHasVoted(prev => ({...prev, [data.poll_id]: false}));
                  setVoteResults(prev => ({...prev, [data.poll_id]: {}}));
                  
                  // Start timer if specified
                  if (data.timer_minutes) {
                    const endTime = Date.now() + (data.timer_minutes * 60 * 1000);
                    setPollTimers(prev => ({...prev, [data.poll_id]: endTime}));
                  }
                  break;
                case 'poll_stopped':
                  setActivePolls(prev => prev.filter(poll => poll.poll_id !== data.poll_id));
                  break;
                case 'poll_auto_stopped':
                  setActivePolls(prev => prev.filter(poll => poll.poll_id !== data.poll_id));
                  setPollTimers(prev => {
                    const newTimers = {...prev};
                    delete newTimers[data.poll_id];
                    return newTimers;
                  });
                  break;
                case 'participant_approved':
                  if (data.participant_token === participantToken) {
                    setApprovalStatus('approved');
                  }
                  break;
                case 'participant_denied':
                  if (data.participant_token === participantToken) {
                    setApprovalStatus('denied');
                  }
                  break;
                case 'vote_update':
                  setVoteResults(prev => ({
                    ...prev,
                    [data.poll_id]: data.vote_counts
                  }));
                  // Also reload all polls to get updated data for organizer
                  if (roomData && roomData.room_id) {
                    loadAllPolls(roomData.room_id);
                  }
                  break;
                default:
                  break;
              }
            } catch (parseError) {
              console.error('WebSocket message parse error:', parseError);
            }
          };
          
          websocket.onclose = (event) => {
            console.log('WebSocket disconnected', event);
            
            // Try to reconnect if not a normal closure
            if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
              reconnectAttempts++;
              console.log(`Attempting to reconnect... (${reconnectAttempts}/${maxReconnectAttempts})`);
              setTimeout(connectWebSocket, 2000 * reconnectAttempts); // Exponential backoff
            }
          };
          
          websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
          };
          
          setWs(websocket);
          
        } catch (wsError) {
          console.error('WebSocket connection error:', wsError);
        }
      };
      
      connectWebSocket();
      
      return () => {
        if (websocket) {
          websocket.close(1000, 'Component unmounting');
        }
      };
    }
  }, [roomData, participantToken]);

  // Create Room (Organizer)
  const createRoom = async (organizerName, customRoomId = '') => {
    try {
      const params = new URLSearchParams({ organizer_name: organizerName });
      if (customRoomId) {
        params.append('custom_room_id', customRoomId);
      }
      
      const response = await fetch(`${BACKEND_URL}/api/rooms/create?${params}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create room');
      }
      
      const data = await response.json();
      setRoomData(data);
      setCurrentView('organizer');
      loadRoomStatus(data.room_id);
    } catch (error) {
      alert('Error creating room: ' + error.message);
    }
  };

  // Join Room (Participant) with enhanced error handling
  const joinRoom = async (roomId, participantName) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/rooms/join?room_id=${roomId}&participant_name=${encodeURIComponent(participantName)}`, {
        method: 'POST',
        timeout: 15000 // 15 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        if (response.status === 404) {
          throw new Error('Room not found. Please check the Room ID and try again.');
        }
        
        if (response.status === 400) {
          throw new Error(errorData.detail || 'Invalid room ID or participant name.');
        }
        
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      setRoomData(data);
      setParticipantToken(data.participant_token);
      setApprovalStatus(data.approval_status);
      setCurrentView('participant');
      
      // Load room status to check for existing active polls
      loadRoomStatus(roomId);
      
    } catch (error) {
      console.error('Join room error:', error);
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network connection failed. Please check your internet connection and try again.');
      }
      throw error;
    }
  };

  // Load participants
  const loadParticipants = async (roomId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/rooms/${roomId}/participants`);
      const data = await response.json();
      setParticipants(data.participants);
    } catch (error) {
      console.error('Error loading participants:', error);
    }
  };

  // Auto-refresh participants every 5 seconds when in organizer view
  useEffect(() => {
    let interval;
    if (currentView === 'organizer' && roomData && roomData.room_id) {
      interval = setInterval(() => {
        loadParticipants(roomData.room_id);
        loadRoomStatus(roomData.room_id);
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentView, roomData]);

  // Approve participant
  const approveParticipant = async (participantId) => {
    try {
      await fetch(`${BACKEND_URL}/api/participants/${participantId}/approve`, {
        method: 'POST'
      });
      if (roomData && roomData.room_id) {
        loadParticipants(roomData.room_id);
        loadRoomStatus(roomData.room_id);
      }
    } catch (error) {
      alert('Error approving participant: ' + error.message);
    }
  };

  // Deny participant
  const denyParticipant = async (participantId) => {
    try {
      await fetch(`${BACKEND_URL}/api/participants/${participantId}/deny`, {
        method: 'POST'
      });
      if (roomData && roomData.room_id) {
        loadParticipants(roomData.room_id);
        loadRoomStatus(roomData.room_id);
      }
    } catch (error) {
      alert('Error denying participant: ' + error.message);
    }
  };

  // Load all polls for the room
  const loadAllPolls = async (roomId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/rooms/${roomId}/polls`);
      const data = await response.json();
      setAllPolls(data.polls);
      setCreatedPolls(data.polls);
    } catch (error) {
      console.error('Error loading polls:', error);
    }
  };

  // Load room status
  const loadRoomStatus = async (roomId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/rooms/${roomId}/status`);
      const data = await response.json();
      setRoomStatus(data);
      if (data.active_polls) {
        setActivePolls(data.active_polls);
      }
      // Load all polls for the organizer
      loadAllPolls(roomId);
    } catch (error) {
      console.error('Error loading room status:', error);
    }
  };

  // Create Poll
  const createPoll = async (question, options, timerMinutes = null) => {
    try {
      const pollData = {
        room_id: roomData.room_id,
        question,
        options
      };
      
      if (timerMinutes) {
        pollData.timer_minutes = timerMinutes;
      }
      
      const response = await fetch(`${BACKEND_URL}/api/polls/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pollData)
      });
      
      const newPoll = await response.json();
      setCreatedPolls(prev => [...prev, newPoll]);
      loadRoomStatus(roomData.room_id);
    } catch (error) {
      alert('Error creating poll: ' + error.message);
    }
  };

  // Start Poll
  const startPoll = async (pollId) => {
    try {
      await fetch(`${BACKEND_URL}/api/polls/${pollId}/start`, {
        method: 'POST'
      });
      // Reload room status to update UI
      if (roomData && roomData.room_id) {
        loadRoomStatus(roomData.room_id);
      }
    } catch (error) {
      alert('Error starting poll: ' + error.message);
    }
  };

  // Stop Poll
  const stopPoll = async (pollId) => {
    try {
      await fetch(`${BACKEND_URL}/api/polls/${pollId}/stop`, {
        method: 'POST'
      });
    } catch (error) {
      alert('Error stopping poll: ' + error.message);
    }
  };

  // Vote with enhanced error handling and retry
  const vote = async (pollId, selectedOption, retryCount = 0) => {
    const maxRetries = 2;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/polls/${pollId}/vote`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          participant_token: participantToken,
          selected_option: selectedOption
        }),
        timeout: 10000 // 10 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific error cases
        if (response.status === 400 && errorData.detail === 'Already voted') {
          setHasVoted(prev => ({...prev, [pollId]: true}));
          alert('⚠️ You have already voted on this poll.');
          return;
        }
        
        if (response.status === 403 && errorData.detail === 'Participant not approved to vote') {
          alert('⚠️ You need to be approved by the organizer before you can vote.');
          return;
        }
        
        if (response.status === 404) {
          alert('⚠️ This poll is no longer active.');
          return;
        }
        
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }
      
      // Success - mark as voted
      setHasVoted(prev => ({...prev, [pollId]: true}));
      
      // Show success feedback
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
      notification.textContent = '✓ Vote recorded successfully!';
      document.body.appendChild(notification);
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Vote error:', error);
      
      // Retry logic for network errors
      if (retryCount < maxRetries && (
        error.name === 'TypeError' || 
        error.message.includes('fetch') ||
        error.message.includes('Network')
      )) {
        console.log(`Retrying vote... (${retryCount + 1}/${maxRetries})`);
        setTimeout(() => {
          vote(pollId, selectedOption, retryCount + 1);
        }, 1000 * (retryCount + 1)); // Exponential backoff
        return;
      }
      
      // Show user-friendly error message
      alert(
        `❌ Failed to record your vote:\n\n${error.message}\n\n` +
        `Please try again. If the problem persists, contact the organizer.`
      );
    }
  };

  // Enhanced report generation with multiple export options
  const generateReport = async () => {
    try {
      const confirmGenerate = window.confirm(
        '📊 Export Meeting Data?\n\n' +
        'This will:\n' +
        '• Generate a complete meeting report\n' +
        '• Export data in multiple formats for reliability\n' +
        '• Permanently delete ALL meeting data after successful export\n\n' +
        'Continue?'
      );
      
      if (!confirmGenerate) {
        return;
      }
      
      console.log('Starting report generation...');
      
      // Method 1: Try PDF download first
      let pdfSuccess = false;
      try {
        const pdfResponse = await fetch(`${BACKEND_URL}/api/rooms/${roomData.room_id}/report`);
        
        if (pdfResponse.ok && pdfResponse.headers.get('Content-Type')?.includes('application/pdf')) {
          const blob = await pdfResponse.blob();
          
          if (blob.size > 0) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `poll_report_${roomData.room_id}_${new Date().toISOString().slice(0,19).replace(/[T:]/g, '_')}.pdf`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            pdfSuccess = true;
            console.log('PDF download successful');
          }
        }
      } catch (pdfError) {
        console.warn('PDF download failed:', pdfError);
      }
      
      // Method 2: JSON backup export (always generate)
      let jsonSuccess = false;
      try {
        const jsonResponse = await fetch(`${BACKEND_URL}/api/rooms/${roomData.room_id}/status`);
        const pollsResponse = await fetch(`${BACKEND_URL}/api/rooms/${roomData.room_id}/polls`);
        const participantsResponse = await fetch(`${BACKEND_URL}/api/rooms/${roomData.room_id}/participants`);
        
        if (jsonResponse.ok && pollsResponse.ok && participantsResponse.ok) {
          const roomStatus = await jsonResponse.json();
          const pollsData = await pollsResponse.json();
          const participantsData = await participantsResponse.json();
          
          const completeReport = {
            exported_at: new Date().toISOString(),
            room_info: {
              room_id: roomData.room_id,
              organizer_name: roomData.organizer_name,
              participant_count: roomStatus.participant_count,
              approved_count: roomStatus.approved_count,
              total_polls: roomStatus.total_polls
            },
            participants: participantsData.participants.map(p => ({
              name: p.participant_name,
              approval_status: p.approval_status,
              joined_at: p.joined_at
            })),
            polls: pollsData.polls.map(poll => ({
              question: poll.question,
              options: poll.options,
              vote_counts: poll.vote_counts,
              total_votes: poll.total_votes,
              was_active: poll.is_active,
              created_at: poll.created_at
            }))
          };
          
          // Download as JSON
          const jsonBlob = new Blob([JSON.stringify(completeReport, null, 2)], { type: 'application/json' });
          const jsonUrl = URL.createObjectURL(jsonBlob);
          const jsonA = document.createElement('a');
          jsonA.href = jsonUrl;
          jsonA.download = `poll_data_${roomData.room_id}_${new Date().toISOString().slice(0,19).replace(/[T:]/g, '_')}.json`;
          jsonA.style.display = 'none';
          document.body.appendChild(jsonA);
          jsonA.click();
          document.body.removeChild(jsonA);
          URL.revokeObjectURL(jsonUrl);
          jsonSuccess = true;
          console.log('JSON backup successful');
        }
      } catch (jsonError) {
        console.error('JSON export failed:', jsonError);
      }
      
      // Method 3: Text report as final fallback
      let textSuccess = false;
      try {
        const textReport = generateTextReport();
        const textBlob = new Blob([textReport], { type: 'text/plain' });
        const textUrl = URL.createObjectURL(textBlob);
        const textA = document.createElement('a');
        textA.href = textUrl;
        textA.download = `poll_report_${roomData.room_id}_${new Date().toISOString().slice(0,19).replace(/[T:]/g, '_')}.txt`;
        textA.style.display = 'none';
        document.body.appendChild(textA);
        textA.click();
        document.body.removeChild(textA);
        URL.revokeObjectURL(textUrl);
        textSuccess = true;
        console.log('Text report successful');
      } catch (textError) {
        console.error('Text export failed:', textError);
      }
      
      // Check if at least one export method succeeded
      if (!pdfSuccess && !jsonSuccess && !textSuccess) {
        throw new Error('All export methods failed. Please try again or contact support.');
      }
      
      // Show success message
      const methods = [];
      if (pdfSuccess) methods.push('PDF');
      if (jsonSuccess) methods.push('JSON data');  
      if (textSuccess) methods.push('Text report');
      
      alert(`✅ Report exported successfully!\n\nFormats: ${methods.join(', ')}\n\n⏳ Cleaning up meeting data...`);
      
      // Wait for downloads to complete, then cleanup
      setTimeout(async () => {
        try {
          const cleanupResponse = await fetch(`${BACKEND_URL}/api/rooms/${roomData.room_id}/cleanup`, {
            method: 'DELETE'
          });
          
          if (!cleanupResponse.ok) {
            throw new Error(`Cleanup failed: ${cleanupResponse.status}`);
          }
          
          alert('🗑️ All meeting data has been permanently deleted for security.');
          setCurrentView('home');
          setRoomData(null);
          setParticipants([]);
          setCreatedPolls([]);
          setAllPolls([]);
          setRoomStatus(null);
          setActivePolls([]);
          setVoteResults({});
          setPollTimers({});
        } catch (cleanupError) {
          console.error('Error during cleanup:', cleanupError);
          alert(
            '⚠️ Data exported successfully, but there was an issue cleaning up server data.\n\n' +
            'Please contact support to ensure complete data deletion.\n\n' +
            `Error: ${cleanupError.message}`
          );
        }
      }, 5000); // 5 second delay for downloads
      
    } catch (error) {
      console.error('Report generation error:', error);
      alert(
        '❌ Error exporting meeting data:\n\n' +
        `${error.message}\n\n` +
        'Please try again. If the problem persists, contact support.'
      );
    }
  };

  // Generate text report as fallback
  const generateTextReport = () => {
    const timestamp = new Date().toLocaleString();
    let report = `POLL MEETING REPORT\n`;
    report += `========================\n`;
    report += `Room ID: ${roomData.room_id}\n`;
    report += `Organizer: ${roomData.organizer_name}\n`;
    report += `Generated: ${timestamp}\n`;
    report += `Participants: ${roomStatus?.participant_count || 0}\n`;
    report += `Approved: ${roomStatus?.approved_count || 0}\n\n`;
    
    // Add participant list
    if (participants.length > 0) {
      report += `PARTICIPANTS:\n`;
      report += `-------------\n`;
      participants.forEach((p, i) => {
        report += `${i + 1}. ${p.participant_name} (${p.approval_status})\n`;
      });
      report += `\n`;
    }
    
    // Add poll results
    if (allPolls.length > 0) {
      report += `POLL RESULTS:\n`;
      report += `-------------\n`;
      allPolls.forEach((poll, i) => {
        report += `\nPoll ${i + 1}: ${poll.question}\n`;
        report += `Total Votes: ${poll.total_votes || 0}\n`;
        if (poll.total_votes > 0) {
          poll.options.forEach(option => {
            const count = poll.vote_counts?.[option] || 0;
            const percentage = poll.total_votes > 0 ? ((count / poll.total_votes) * 100).toFixed(1) : 0;
            report += `  ${option}: ${count} votes (${percentage}%)\n`;
          });
        } else {
          report += `  No votes recorded\n`;
        }
      });
    } else {
      report += `No polls were created.\n`;
    }
    
    report += `\n---\nReport generated by Secret Poll System`;
    return report;
  };

  // Home View
  if (currentView === 'home') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 py-16">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-gray-800 mb-4">Secret Poll</h1>
            <p className="text-xl text-gray-600">Anonymous polling for meetings</p>
          </div>
          
          <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-8">
            <OrganizerCard onCreateRoom={createRoom} />
            <ParticipantCard onJoinRoom={joinRoom} />
          </div>
        </div>
      </div>
    );
  }

  // Organizer View
  if (currentView === 'organizer') {
    return (
      <div className="min-h-screen bg-gray-50">
        <OrganizerDashboard 
          roomData={roomData}
          roomStatus={roomStatus}
          activePolls={activePolls}
          allPolls={allPolls}
          createdPolls={createdPolls}
          participants={participants}
          pollTimers={pollTimers}
          voteResults={voteResults}
          onCreatePoll={createPoll}
          onStartPoll={startPoll}
          onStopPoll={stopPoll}
          onGenerateReport={generateReport}
          onApproveParticipant={approveParticipant}
          onDenyParticipant={denyParticipant}
          onLoadParticipants={loadParticipants}
          onBack={() => setCurrentView('home')}
        />
      </div>
    );
  }

  // Participant View
  if (currentView === 'participant') {
    return (
      <div className="min-h-screen bg-gray-50">
        <ParticipantView 
          roomData={roomData}
          activePolls={activePolls}
          allPolls={allPolls}
          hasVoted={hasVoted}
          approvalStatus={approvalStatus}
          voteResults={voteResults}
          pollTimers={pollTimers}
          onVote={vote}
          onBack={() => setCurrentView('home')}
        />
      </div>
    );
  }

  return null;
}

// Organizer Card Component
function OrganizerCard({ onCreateRoom }) {
  const [organizerName, setOrganizerName] = useState('');
  const [customRoomId, setCustomRoomId] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (organizerName.trim()) {
      // Validate custom room ID if provided
      if (customRoomId && customRoomId.length < 3) {
        alert('Custom room ID must be at least 3 characters long');
        return;
      }
      onCreateRoom(organizerName.trim(), customRoomId.trim());
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h3M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 4h1m4 0h1" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Start a Meeting</h2>
        <p className="text-gray-600">Create polls and manage your meeting</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
          <input
            type="text"
            value={organizerName}
            onChange={(e) => setOrganizerName(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter your name"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Custom Room ID (Optional)</label>
          <input
            type="text"
            value={customRoomId}
            onChange={(e) => {
              // Only allow alphanumeric characters and limit to 10 chars
              const value = e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 10);
              setCustomRoomId(value);
            }}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
            placeholder="e.g., MEETING01 (3-10 characters, letters & numbers only)"
            maxLength={10}
          />
          <p className="text-xs text-gray-500 mt-1">
            {customRoomId.length > 0 && customRoomId.length < 3 && (
              <span className="text-red-500">Minimum 3 characters required</span>
            )}
            {customRoomId.length >= 3 && (
              <span className="text-green-600">✓ Valid room ID</span>
            )}
            {customRoomId.length === 0 && (
              <span>Custom IDs help identify meetings (leave empty for random ID)</span>
            )}
          </p>
        </div>
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Create Room
        </button>
      </form>
    </div>
  );
}

// Participant Card Component
function ParticipantCard({ onJoinRoom }) {
  const [roomId, setRoomId] = useState('');
  const [participantName, setParticipantName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate inputs
    const trimmedRoomId = roomId.trim().toUpperCase();
    const trimmedName = participantName.trim();
    
    if (!trimmedRoomId) {
      alert('Please enter a Room ID');
      return;
    }
    
    if (!trimmedName) {
      alert('Please enter your name');
      return;
    }
    
    if (trimmedName.length < 2) {
      alert('Name must be at least 2 characters long');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      await onJoinRoom(trimmedRoomId, trimmedName);
    } catch (error) {
      console.error('Join room error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Join a Meeting</h2>
        <p className="text-gray-600">Enter your details to participate</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Your Name</label>
          <input
            type="text"
            value={participantName}
            onChange={(e) => setParticipantName(e.target.value)}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent ${
              participantName.trim().length >= 2 ? 'border-gray-300' : 'border-red-300'
            }`}
            placeholder="Enter your name"
            disabled={isSubmitting}
            maxLength={50}
          />
          {participantName.trim().length > 0 && participantName.trim().length < 2 && (
            <p className="text-red-500 text-xs mt-1">Name must be at least 2 characters</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Room ID</label>
          <input
            type="text"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value.toUpperCase())}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-center text-lg font-mono ${
              roomId.trim().length >= 3 ? 'border-gray-300' : 'border-red-300'
            }`}
            placeholder="Enter Room ID"
            disabled={isSubmitting}
            maxLength={10}
          />
          {roomId.trim().length > 0 && roomId.trim().length < 3 && (
            <p className="text-red-500 text-xs mt-1">Room ID must be at least 3 characters</p>
          )}
        </div>
        <button
          type="submit"
          disabled={isSubmitting || !roomId.trim() || !participantName.trim() || participantName.trim().length < 2}
          className="w-full bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isSubmitting ? '⏳ Joining...' : 'Join Room'}
        </button>
        <p className="text-xs text-gray-500 text-center">
          💡 You can join and participate even while polls are active
        </p>
      </form>
    </div>
  );
}

// Organizer Dashboard Component
function OrganizerDashboard({ 
  roomData, 
  roomStatus, 
  activePolls, 
  allPolls,
  createdPolls,
  participants,
  pollTimers,
  voteResults, 
  onCreatePoll, 
  onStartPoll, 
  onStopPoll, 
  onGenerateReport,
  onApproveParticipant,
  onDenyParticipant,
  onLoadParticipants,
  onBack 
}) {
  const [showPollForm, setShowPollForm] = useState(false);
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState(['', '']);
  const [timerMinutes, setTimerMinutes] = useState('');

  // Load participants when component mounts
  useEffect(() => {
    if (roomData && roomData.room_id) {
      onLoadParticipants(roomData.room_id);
    }
  }, [roomData, onLoadParticipants]);

  const handleCreatePoll = (e) => {
    e.preventDefault();
    const validOptions = options.filter(opt => opt.trim());
    if (question.trim() && validOptions.length >= 2) {
      const pollData = {
        question: question.trim(),
        options: validOptions
      };
      
      // Add timer if specified
      if (timerMinutes && parseInt(timerMinutes) > 0) {
        pollData.timer_minutes = parseInt(timerMinutes);
      }
      
      onCreatePoll(pollData.question, pollData.options, pollData.timer_minutes);
      setQuestion('');
      setOptions(['', '']);
      setTimerMinutes('');
      setShowPollForm(false);
    }
  };

  const addOption = () => {
    setOptions([...options, '']);
  };

  const updateOption = (index, value) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const removeOption = (index) => {
    if (options.length > 2) {
      setOptions(options.filter((_, i) => i !== index));
    }
  };

  const pendingParticipants = participants.filter(p => p.approval_status === 'pending');
  const approvedParticipants = participants.filter(p => p.approval_status === 'approved');

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Meeting Dashboard</h1>
            <p className="text-gray-600 mt-2">Room ID: <span className="font-mono font-bold text-lg">{roomData?.room_id}</span></p>
          </div>
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            ← Back
          </button>
        </div>
        
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="font-semibold text-blue-800 mb-2">Total Participants</h3>
            <p className="text-2xl font-bold text-blue-600">{roomStatus?.participant_count || 0}</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <h3 className="font-semibold text-green-800 mb-2">Approved</h3>
            <p className="text-2xl font-bold text-green-600">{roomStatus?.approved_count || 0}</p>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4">
            <h3 className="font-semibold text-yellow-800 mb-2">Pending</h3>
            <p className="text-2xl font-bold text-yellow-600">{roomStatus?.pending_count || 0}</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <h3 className="font-semibold text-purple-800 mb-2">Active Polls</h3>
            <p className="text-2xl font-bold text-purple-600">{activePolls?.length || 0}</p>
          </div>
        </div>

        <div className="flex gap-4">
          <button
            onClick={() => setShowPollForm(!showPollForm)}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {showPollForm ? 'Cancel' : 'Create New Poll'}
          </button>
          <button
            onClick={onGenerateReport}
            className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors"
          >
            📄 Generate PDF Report & End Meeting
          </button>
        </div>
      </div>

      {/* Participant Management Section */}
      {pendingParticipants.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Pending Participants</h2>
          <div className="space-y-3">
            {pendingParticipants.map((participant) => (
              <div key={participant.participant_id} className="flex justify-between items-center p-4 bg-yellow-50 rounded-lg">
                <div>
                  <h4 className="font-medium text-gray-800">{participant.participant_name}</h4>
                  <p className="text-sm text-gray-600">Joined: {new Date(participant.joined_at).toLocaleTimeString()}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onApproveParticipant(participant.participant_id)}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => onDenyParticipant(participant.participant_id)}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm"
                  >
                    Deny
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approved Participants Section */}
      {approvedParticipants.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Approved Participants</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {approvedParticipants.map((participant) => (
              <div key={participant.participant_id} className="p-3 bg-green-50 rounded-lg">
                <span className="font-medium text-green-800">{participant.participant_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {showPollForm && (
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Create New Poll</h2>
          <form onSubmit={handleCreatePoll} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Question</label>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your question"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Options</label>
              {options.map((option, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={option}
                    onChange={(e) => updateOption(index, e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder={`Option ${index + 1}`}
                    required
                  />
                  {options.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removeOption(index)}
                      className="px-3 py-2 text-red-600 hover:text-red-800"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addOption}
                className="text-blue-600 hover:text-blue-800 text-sm"
              >
                + Add Option
              </button>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Auto-Stop Timer (Optional)</label>
              <input
                type="number"
                value={timerMinutes}
                onChange={(e) => setTimerMinutes(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Minutes (leave empty for manual stop)"
                min="1"
                max="60"
              />
              <p className="text-xs text-gray-500 mt-1">Poll will automatically stop after specified minutes</p>
            </div>
            
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Poll
            </button>
          </form>
        </div>
      )}

      {/* All Polls Management Section */}
      {allPolls.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Poll Management</h2>
          <div className="space-y-4">
            {allPolls.map((poll) => (
              <div key={poll.poll_id} className={`p-4 rounded-lg border-2 ${
                poll.is_active 
                  ? 'border-green-500 bg-green-50' 
                  : poll.total_votes > 0 
                    ? 'border-gray-400 bg-gray-100' 
                    : 'border-gray-300 bg-gray-50'
              }`}>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold text-gray-800">
                        {poll.question}
                      </h4>
                      {poll.is_active && (
                        <span className="px-2 py-1 bg-green-600 text-white text-xs rounded-full">ACTIVE</span>
                      )}
                      {!poll.is_active && poll.total_votes > 0 && (
                        <span className="px-2 py-1 bg-gray-600 text-white text-xs rounded-full">CLOSED</span>
                      )}
                      {poll.is_active && pollTimers[poll.poll_id] && (
                        <PollTimer endTime={pollTimers[poll.poll_id]} />
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">Options: {poll.options.join(', ')}</p>
                    <p className="text-sm text-gray-500 mb-2">Total votes: {poll.total_votes || 0}</p>
                    
                    {/* Show live vote breakdown */}
                    {poll.total_votes > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-sm font-medium text-gray-700">Live Results:</p>
                        {poll.options.map(option => {
                          const count = poll.vote_counts[option] || 0;
                          const percentage = poll.total_votes > 0 ? ((count / poll.total_votes) * 100).toFixed(1) : 0;
                          return (
                            <div key={option} className="bg-white rounded p-2">
                              <div className="flex justify-between text-sm mb-1">
                                <span>{option}:</span>
                                <span className="font-medium">{count} votes ({percentage}%)</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full transition-all duration-300 ${
                                    poll.is_active ? 'bg-green-600' : 'bg-gray-600'
                                  }`}
                                  style={{ width: `${percentage}%` }}
                                ></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    {poll.is_active ? (
                      <button
                        onClick={() => onStopPoll(poll.poll_id)}
                        className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors"
                      >
                        Stop
                      </button>
                    ) : poll.total_votes === 0 ? (
                      <button
                        onClick={() => onStartPoll(poll.poll_id)}
                        className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors"
                      >
                        Start
                      </button>
                    ) : (
                      <span className="px-3 py-1 text-xs text-gray-500 bg-gray-200 rounded">
                        Final Results
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Participant View Component
function ParticipantView({ roomData, activePolls, allPolls, hasVoted, approvalStatus, voteResults, pollTimers, onVote, onBack }) {
  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Poll Meeting</h1>
            <p className="text-gray-600 mt-2">Organizer: {roomData?.organizer_name}</p>
            <p className="text-gray-600">Room: <span className="font-mono font-bold">{roomData?.room_id}</span></p>
          </div>
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            ← Leave
          </button>
        </div>
      </div>

      {/* Approval Status Messages */}
      {approvalStatus === 'pending' && (
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Waiting for Approval</h2>
          <p className="text-gray-600">The organizer needs to approve you before you can participate in polls.</p>
          <p className="text-sm text-gray-500 mt-2">Name: {roomData?.participant_name}</p>
        </div>
      )}

      {approvalStatus === 'denied' && (
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Access Denied</h2>
          <p className="text-gray-600">The organizer has denied your request to participate in this meeting.</p>
        </div>
      )}

      {/* Only show polls if approved */}
      {approvalStatus === 'approved' && (!activePolls || activePolls.length === 0) && (
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Waiting for Polls</h2>
          <p className="text-gray-600">The organizer will start polls soon...</p>
        </div>
      )}

      {/* Show all active polls */}
      {approvalStatus === 'approved' && activePolls && activePolls.length > 0 && (
        <div className="space-y-6">
          {activePolls.map((poll) => (
            <div key={poll.poll_id} className="bg-white rounded-2xl shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-800">Active Poll</h2>
                {pollTimers[poll.poll_id] && (
                  <PollTimer endTime={pollTimers[poll.poll_id]} />
                )}
              </div>
              <h3 className="text-xl text-gray-700 mb-6">{poll.question}</h3>
              
              {!hasVoted[poll.poll_id] ? (
                // Voting interface WITHOUT showing results
                <div>
                  <div className="space-y-3 mb-6">
                    {poll.options?.map((option, index) => (
                      <button
                        key={index}
                        onClick={() => onVote(poll.poll_id, option)}
                        className="w-full p-4 text-left bg-gray-50 hover:bg-blue-50 border border-gray-200 hover:border-blue-300 rounded-lg transition-colors relative"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{option}</span>
                          {/* NO vote counts shown before voting */}
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg text-center">
                    <p className="text-blue-800 text-sm font-medium">
                      🗳️ Make your choice • Results will be shown after you vote
                    </p>
                  </div>
                </div>
              ) : (
                // Results display after voting
                <div>
                  <div className="space-y-3 mb-6">
                    {poll.options?.map((option, index) => {
                      const count = voteResults[poll.poll_id]?.[option] || 0;
                      const total = Object.values(voteResults[poll.poll_id] || {}).reduce((sum, count) => sum + count, 0);
                      const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                      
                      return (
                        <div key={index} className="bg-gray-50 rounded-lg p-4">
                          <div className="flex justify-between items-center mb-2">
                            <span className="font-medium">{option}</span>
                            <span className="text-gray-600">{count} votes ({percentage}%)</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-green-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${percentage}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  <div className="p-4 bg-green-50 rounded-lg">
                    <p className="text-green-800 font-medium">✓ Your vote has been recorded anonymously</p>
                    <p className="text-green-700 text-sm">Results update automatically as others vote</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      
      {/* Show closed polls with final results */}
      {approvalStatus === 'approved' && allPolls && allPolls.length > 0 && (
        <div className="space-y-6">
          {allPolls.filter(poll => !poll.is_active && poll.total_votes > 0).map((poll) => (
            <div key={poll.poll_id} className="bg-white rounded-2xl shadow-lg p-6 border-2 border-gray-400">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-800">Poll Results</h2>
                <span className="px-3 py-1 bg-gray-600 text-white text-sm rounded-full font-medium">
                  CLOSED
                </span>
              </div>
              <h3 className="text-xl text-gray-700 mb-6">{poll.question}</h3>
              
              <div className="space-y-3 mb-4">
                {poll.options?.map((option, index) => {
                  const count = poll.vote_counts?.[option] || 0;
                  const total = poll.total_votes || 0;
                  const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                  
                  return (
                    <div key={index} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium">{option}</span>
                        <span className="text-gray-600">{count} votes ({percentage}%)</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-gray-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              <div className="p-3 bg-gray-100 rounded-lg text-center">
                <p className="text-gray-700 text-sm font-medium">
                  Final Results • Total Votes: {poll.total_votes}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Timer Component
function PollTimer({ endTime, onTimerEnd }) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    const updateTimer = () => {
      const now = Date.now();
      const diff = endTime - now;
      
      if (diff <= 0) {
        setTimeLeft('TIME UP');
        if (onTimerEnd) onTimerEnd();
        return;
      }
      
      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      setTimeLeft(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [endTime, onTimerEnd]);

  if (!timeLeft) return null;

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
      timeLeft === 'TIME UP' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
    }`}>
      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {timeLeft}
    </div>
  );
}

export default App;