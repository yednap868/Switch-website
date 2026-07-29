const twilio = require('twilio');

function setupTwilioHandlers(app, myOperator) {
  
  // When employer call reaches Twilio (via Click2Call)
  app.post('/api/twilio/incoming', (req, res) => {
    const callerNumber = req.body.From;
    const callSid = req.body.CallSid;
    
    console.log('📞 Twilio incoming call from:', callerNumber);
    console.log('📞 Call SID:', callSid);
    
    const VoiceResponse = twilio.twiml.VoiceResponse;
    const response = new VoiceResponse();

    // Connect to ElevenLabs Conversational AI
    const connect = response.connect();
    connect.conversationalAi({
      provider: 'elevenlabs',
      elevenlabs: {
        agentId: process.env.ELEVENLABS_AGENT_ID,
        apiKey: process.env.ELEVENLABS_API_KEY
      }
    });

    // Store call info
    global.activeCalls = global.activeCalls || new Map();
    global.activeCalls.set(callSid, {
      employer_number: callerNumber,
      employer_call_sid: callSid,
      status: 'ai_collecting_requirements',
      timestamp: Date.now()
    });

    res.type('text/xml');
    res.send(response.toString());
  });

  // When candidate picks up (via Click2Call)
  app.post('/api/twilio/candidate-connected', (req, res) => {
    const candidatePhone = req.body.From;
    const candidateCallSid = req.body.CallSid;
    const employerCallSid = req.query.employer_call_sid;
    
    console.log(`✅ Candidate connected: ${candidatePhone}`);
    console.log(`📞 Candidate Call SID: ${candidateCallSid}`);
    console.log(`📞 Employer Call SID: ${employerCallSid}`);
    
    const VoiceResponse = twilio.twiml.VoiceResponse;
    const response = new VoiceResponse();

    // Quick intro in Hindi
    response.say({
      voice: 'Polly.Aditi',
      language: 'hi-IN'
    }, 'Namaste! Main Switch AI hoon. Ek company aapse abhi interview karna chahti hai. Connecting you now.');

    response.pause({ length: 2 });

    // Connect to conference with employer
    const dial = response.dial();
    dial.conference({
      name: `match_${employerCallSid}`,
      startConferenceOnEnter: true,
      endConferenceOnExit: true,
      recordingStatusCallback: `${process.env.SERVER_URL}/api/recording-complete`,
      statusCallback: `${process.env.SERVER_URL}/api/conference-status`,
      statusCallbackEvent: ['start', 'end', 'join', 'leave']
    });

    // Update active call status
    if (global.activeCalls && global.activeCalls.has(employerCallSid)) {
      const callInfo = global.activeCalls.get(employerCallSid);
      callInfo.candidate_call_sid = candidateCallSid;
      callInfo.candidate_phone = candidatePhone;
      callInfo.status = 'connected';
      callInfo.connected_at = Date.now();
    }

    res.type('text/xml');
    res.send(response.toString());
  });

  // Move employer to conference after ElevenLabs finishes
  app.post('/api/twilio/employer-to-conference', (req, res) => {
    const callSid = req.body.CallSid || req.query.call_sid;
    
    console.log('🔄 Moving employer to conference:', callSid);
    
    const VoiceResponse = twilio.twiml.VoiceResponse;
    const response = new VoiceResponse();

    response.say({
      voice: 'Polly.Aditi',
      language: 'hi-IN'
    }, 'Perfect! Main candidates ko call kar raha hoon. Kripya 15 seconds wait karein.');

    // Join conference
    const dial = response.dial();
    dial.conference({
      name: `match_${callSid}`,
      waitUrl: 'http://twimlets.com/holdmusic?Bucket=com.twilio.music.classical',
      startConferenceOnEnter: true,
      endConferenceOnExit: true,
      statusCallback: `${process.env.SERVER_URL}/api/conference-status`,
      statusCallbackEvent: ['start', 'end', 'join', 'leave']
    });

    res.type('text/xml');
    res.send(response.toString());
  });

  // Conference status callback
  app.post('/api/conference-status', (req, res) => {
    const event = req.body.StatusCallbackEvent;
    const conferenceName = req.body.FriendlyName;
    const participant = req.body.CallSid;
    
    console.log(`📞 Conference ${conferenceName} event: ${event}`);
    console.log(`👤 Participant: ${participant}`);
    
    if (event === 'conference-end') {
      console.log('✅ Call completed');
      // TODO: Send WhatsApp to both parties with next steps
      
      // Clean up active call
      if (global.activeCalls) {
        const employerCallSid = conferenceName.replace('match_', '');
        global.activeCalls.delete(employerCallSid);
      }
    }
    
    res.sendStatus(200);
  });

  // Recording complete callback
  app.post('/api/recording-complete', (req, res) => {
    const recordingUrl = req.body.RecordingUrl;
    const callSid = req.body.CallSid;
    
    console.log('🎙️ Recording available:', recordingUrl);
    console.log('📞 Call SID:', callSid);
    
    // TODO: Save recording URL to database
    // TODO: Send recording link via WhatsApp
    
    res.sendStatus(200);
  });
}

module.exports = { setupTwilioHandlers };
