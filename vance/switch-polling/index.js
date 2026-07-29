const express = require('express');
const bodyParser = require('body-parser');
require('dotenv').config();

const MyOperatorAPI = require('./myoperator');
const { setupTwilioHandlers } = require('./twilio-handlers');
const { findMatchingCandidates, getCandidateByPhone } = require('./candidates');

const app = express();
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

// Initialize MyOperator
const myOperator = new MyOperatorAPI(process.env.MYOPERATOR_X_API_KEY);

// Track processed calls to avoid duplicates
const processedCalls = new Set();
let lastPollTime = Date.now() - 300000; // Start from 5 minutes ago to catch recent calls

// Initialize active calls map
global.activeCalls = new Map();

// POLLING LOGIC - Check for new calls every 2 seconds
setInterval(async () => {
  try {
    const now = Date.now();
    const calls = await myOperator.getCallLogs(lastPollTime, now);
    
    // Debug: Log what we're getting from API
    if (calls.length > 0) {
      console.log(`📊 Found ${calls.length} calls in this poll`);
      calls.forEach((call, idx) => {
        console.log(`  Call ${idx + 1}:`, {
          id: call.call_id || call.id,
          direction: call.direction,
          status: call.status,
          from: call.caller_number || call.from,
          to: call.receiver_number || call.to,
          timestamp: call.timestamp || call.created_at
        });
      });
    }
    
    // Update last poll time
    lastPollTime = now;
    
    // Process new incoming calls
    for (const call of calls) {
      // Only process incoming calls we haven't seen before
      const callId = call.call_id || call.id || `${call.caller_number || call.from}_${call.timestamp || Date.now()}`;
      
      // Check all possible status values - also accept "answered" to catch calls quickly
      const isActiveStatus = ['ringing', 'in-progress', 'answered', 'connected', 'ongoing', 'completed'].includes(call.status?.toLowerCase());
      const isIncoming = call.direction === 'incoming' || call.direction === 'in' || call.type === 'incoming';
      
      // Process incoming calls that are active OR recently completed (within last 10 seconds)
      const callAge = Date.now() - ((call.timestamp || call.created_at) * 1000);
      const isRecent = callAge < 10000; // 10 seconds
      
      if (isIncoming && !processedCalls.has(callId) && (isActiveStatus || (call.status === 'completed' && isRecent))) {
        console.log(`📞 New employer call detected: ${call.caller_number || call.from}`);
        console.log(`📞 Call ID: ${callId}`);
        console.log(`📞 Status: ${call.status}`);
        console.log(`📞 Full call object:`, JSON.stringify(call, null, 2));
        
        // Mark as processed
        processedCalls.add(callId);
        
        // Handle the employer call
        await handleEmployerCall(call, callId);
      } else if (isIncoming && !processedCalls.has(callId)) {
        // Log why we're not processing it
        console.log(`⚠️ Incoming call not processed:`, {
          callId,
          direction: call.direction,
          status: call.status,
          reason: !isActiveStatus ? 'Status not active' : 'Already processed'
        });
      }
    }
  } catch (error) {
    console.error('❌ Polling error:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', JSON.stringify(error.response.data, null, 2));
    } else {
      console.error('Full error:', error);
    }
  }
}, 1000); // Poll every 1 second for faster detection

// Handle new employer calls
async function handleEmployerCall(call, callId) {
  try {
    const employerNumber = call.caller_number || call.from;
    console.log(`🔄 Processing employer call from ${employerNumber}...`);
    console.log(`   Call ID: ${callId}`);
    console.log(`   Status: ${call.status}`);
    console.log(`   Timestamp: ${new Date((call.timestamp || call.created_at) * 1000).toISOString()}`);
    
    // IMPORTANT: MyOperator needs to be configured to forward calls to Twilio
    // Click2Call won't work for intercepting active calls
    // Instead, configure MyOperator dashboard:
    // 1. Go to MyOperator dashboard → Call Routing
    // 2. Set incoming calls to forward to: ${process.env.TWILIO_US_NUMBER}
    // 3. This will bypass IVR and send calls directly to Twilio
    
    // For now, log that we detected the call
    // The actual forwarding should be configured in MyOperator dashboard
    console.log(`⚠️  Call detected but forwarding must be configured in MyOperator dashboard`);
    console.log(`   Configure MyOperator to forward to: ${process.env.TWILIO_US_NUMBER}`);
    console.log(`   Or set up webhook URL: ${process.env.SERVER_URL || 'http://your-server.com'}/api/myoperator/webhook`);
    
    // Store call info for tracking
    global.activeCalls = global.activeCalls || new Map();
    global.activeCalls.set(callId, {
      employer_number: employerNumber,
      call_id: callId,
      status: 'detected',
      timestamp: Date.now(),
      note: 'Forwarding must be configured in MyOperator dashboard'
    });
    
  } catch (error) {
    console.error('Error handling employer call:', error.message);
    if (error.response) {
      console.error('Error response:', error.response.data);
    }
  }
}

// MyOperator Webhook - Receive real-time call notifications
app.post('/api/myoperator/webhook', (req, res) => {
  try {
    const webhookData = req.body;
    console.log('🔔 MyOperator Webhook received:', JSON.stringify(webhookData, null, 2));
    
    // Handle different webhook event types
    if (webhookData.event === 'call_started' || webhookData.event === 'incoming_call') {
      const callId = webhookData.call_id || webhookData.id || `${webhookData.caller_number}_${Date.now()}`;
      const callerNumber = webhookData.caller_number || webhookData.from;
      
      if (webhookData.direction === 'incoming' || webhookData.type === 'incoming') {
        console.log(`📞 Real-time incoming call detected via webhook: ${callerNumber}`);
        console.log(`📞 Call ID: ${callId}`);
        
        // Mark as processed
        if (!processedCalls.has(callId)) {
          processedCalls.add(callId);
          
          // Handle immediately
          handleEmployerCall({
            call_id: callId,
            id: callId,
            direction: 'incoming',
            status: 'ringing',
            caller_number: callerNumber,
            from: callerNumber,
            timestamp: Math.floor(Date.now() / 1000),
            created_at: Math.floor(Date.now() / 1000)
          }, callId);
        }
      }
    }
    
    res.json({ status: 'ok', received: true });
  } catch (error) {
    console.error('Error processing MyOperator webhook:', error);
    res.status(500).json({ status: 'error', message: error.message });
  }
});

// Setup Twilio webhook routes
setupTwilioHandlers(app, myOperator);

// Webhook from ElevenLabs after collecting requirements
app.post('/api/elevenlabs/requirements', async (req, res) => {
  try {
    const { job_type, location, salary, experience, call_sid, employer_number } = req.body;
    
    console.log(`📋 Requirements received:`, { job_type, location, salary, experience, call_sid });
    
    // Find matching candidates
    const candidates = findMatchingCandidates({
      job_type: job_type || '',
      location: location || '',
      experience: experience || 0
    });
    
    console.log(`👥 Found ${candidates.length} matching candidates`);
    
    if (candidates.length === 0) {
      // No candidates - tell ElevenLabs to inform employer
      console.log('⚠️ No matching candidates found');
      return res.json({ 
        status: 'no_candidates',
        message: 'No matching candidates found'
      });
    }
    
    // Batch call top 10 candidates
    const callResults = await myOperator.batchCallCandidates(
      candidates.slice(0, 10),
      process.env.TWILIO_US_NUMBER,
      process.env.MYOPERATOR_NUMBER
    );
    
    console.log(`📱 Called ${callResults.length} candidates`);
    
    // Store the employer call info
    if (call_sid && global.activeCalls) {
      const callInfo = global.activeCalls.get(call_sid) || {};
      callInfo.requirements = { job_type, location, salary, experience };
      callInfo.candidates_called = callResults;
      callInfo.status = 'calling_candidates';
      callInfo.candidates_called_at = Date.now();
      global.activeCalls.set(call_sid, callInfo);
    }
    
    // Trigger Twilio to move employer to conference
    // This will be called by ElevenLabs via webhook or we can do it here
    setTimeout(async () => {
      try {
        const twilio = require('twilio');
        const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
        
        // Update the call to redirect to conference
        await client.calls(call_sid).update({
          url: `${process.env.SERVER_URL}/api/twilio/employer-to-conference?call_sid=${call_sid}`,
          method: 'POST'
        });
        
        console.log('✅ Employer moved to conference');
      } catch (error) {
        console.error('Error moving employer to conference:', error.message);
      }
    }, 2000);
    
    res.json({ 
      status: 'success',
      candidates_called: callResults.length,
      message: `Calling ${callResults.length} candidates now`
    });
    
  } catch (error) {
    console.error('Error processing requirements:', error);
    res.status(500).json({ error: error.message });
  }
});

// Webhook for candidate call status (from MyOperator)
app.post('/api/myoperator/candidate-status', (req, res) => {
  const { call_id, status, candidate_phone } = req.body;
  
  console.log(`📞 Candidate call status: ${status} for ${candidate_phone}`);
  
  // If candidate answered, connect them to Twilio
  if (status === 'answered' || status === 'connected') {
    const candidate = getCandidateByPhone(candidate_phone);
    if (candidate) {
      // Find the active employer call
      const employerCallSid = Array.from(global.activeCalls.keys()).find(sid => {
        const callInfo = global.activeCalls.get(sid);
        return callInfo && callInfo.status === 'calling_candidates';
      });
      
      if (employerCallSid) {
        console.log(`✅ Candidate ${candidate.name} answered, connecting to employer...`);
        // The candidate will be connected via Twilio webhook
      }
    }
  }
  
  res.json({ status: 'ok' });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok',
    polling: 'active',
    last_poll: new Date(lastPollTime).toISOString(),
    processed_calls: processedCalls.size,
    active_calls: global.activeCalls ? global.activeCalls.size : 0
  });
});

// Get active calls status
app.get('/api/status', (req, res) => {
  const activeCallsArray = [];
  if (global.activeCalls) {
    for (const [callSid, callInfo] of global.activeCalls.entries()) {
      activeCallsArray.push({
        call_sid: callSid,
        ...callInfo
      });
    }
  }
  
  res.json({
    active_calls: activeCallsArray,
    processed_calls_count: processedCalls.size,
    processed_calls: Array.from(processedCalls),
    last_poll: new Date(lastPollTime).toISOString()
  });
});

// Test endpoint to manually check MyOperator API
app.get('/api/test-myoperator', async (req, res) => {
  try {
    const now = Date.now();
    const timeRange = parseInt(req.query.minutes || '10'); // Default 10 minutes
    const startTime = now - (timeRange * 60000);
    const calls = await myOperator.getCallLogs(startTime, now);
    
    res.json({
      success: true,
      time_range: {
        from: new Date(startTime).toISOString(),
        to: new Date(now).toISOString(),
        minutes: timeRange
      },
      calls_found: calls.length,
      calls: calls,
      sample_call: calls[0] || null,
      all_calls_sample: calls.slice(0, 5) // First 5 calls for debugging
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      response: error.response?.data || null,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Switch AI Server running on port ${PORT}`);
  console.log(`📊 Polling MyOperator every 2 seconds...`);
  console.log(`🔗 Server URL: ${process.env.SERVER_URL || 'Not set - use ngrok'}`);
  console.log(`📞 MyOperator Number: ${process.env.MYOPERATOR_NUMBER}`);
  console.log(`📞 Twilio Number: ${process.env.TWILIO_US_NUMBER}`);
});
