const axios = require('axios');

class MyOperatorAPI {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseURL = 'https://developers.myoperator.co';
  }

  // Get call logs for a time range
  async getCallLogs(startTime, endTime) {
    try {
      const response = await axios.post(
        `${this.baseURL}/search`,
        {
          token: this.apiKey,
          from: Math.floor(startTime / 1000).toString(), // Unix timestamp as string
          to: Math.floor(endTime / 1000).toString(),
          page_size: '100' // Get up to 100 recent calls
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      // Debug: Log the raw response
      console.log('📡 MyOperator API Response:', {
        status: response.status,
        data_keys: Object.keys(response.data || {}),
        has_data: !!response.data.data,
        has_logs: !!response.data.logs,
        full_response_structure: JSON.stringify(response.data).substring(0, 500)
      });
      
      // Check for API errors
      if (response.data.status === 'error') {
        console.error('❌ MyOperator API Error:', response.data.message);
        console.error('   Code:', response.data.code);
        console.error('   This usually means the API token is invalid or not authorized');
        return [];
      }
      
      // MyOperator returns logs in response.data.data.hits array (Elasticsearch format)
      const dataObj = response.data.data || {};
      const logs = dataObj.hits || dataObj.logs || response.data.logs || [];
      
      if (!Array.isArray(logs)) {
        console.warn('⚠️ MyOperator API returned non-array data:', typeof logs);
        console.warn('   Response structure:', JSON.stringify(dataObj).substring(0, 200));
        return [];
      }
      
      console.log(`📊 Found ${logs.length} raw logs from API (total: ${dataObj.total || 'unknown'})`);
      
      // Convert logs to calls format
      // MyOperator returns logs in Elasticsearch format: { _source: { ... } }
      return logs.map(log => {
        // Handle Elasticsearch format where data is in _source
        const source = log._source || log;
        
        // Map direction: 1 = incoming, 0 = outgoing (MyOperator format)
        let direction = source.direction || source.type || source.call_type;
        if (direction === 1 || direction === '1' || source.source === '1' || source.source === 1) {
          direction = 'incoming';
        } else if (direction === 0 || direction === '0' || source.source === '0' || source.source === 0) {
          direction = 'outgoing';
        } else if (typeof direction === 'number') {
          direction = direction === 1 ? 'incoming' : 'outgoing';
        }
        
        // Map status: 2 = completed, 1 = answered, etc.
        let status = source.status || source.call_status;
        if (status === 2 || status === '2') {
          status = 'completed';
        } else if (status === 1 || status === '1') {
          status = 'answered';
        } else if (typeof status === 'number') {
          status = status === 2 ? 'completed' : (status === 1 ? 'answered' : 'ringing');
        }
        
        return {
          call_id: source.id || source.call_id || source.unique_id || source._id || log._id,
          id: source.id || source.call_id || source.unique_id || source._id || log._id,
          direction: direction || 'outgoing',
          status: status || 'completed',
          caller_number: source.caller_number || source.caller || source.from || source.phone || source.caller_number_raw,
          from: source.caller_number || source.caller || source.from || source.phone || source.caller_number_raw,
          receiver_number: source.receiver_number || source.receiver || source.to,
          to: source.receiver_number || source.receiver || source.to,
          timestamp: source.start_time || source._ms || source.timestamp || source.created_at || source.time,
          created_at: source.start_time || source._ms || source.timestamp || source.created_at || source.time,
          duration: source.seconds || source.duration,
          end_time: source.end_time
        };
      });
    } catch (error) {
      console.error('Error fetching call logs:', error.response?.data || error.message);
      if (error.response) {
        console.error('Status:', error.response.status);
        console.error('Data:', JSON.stringify(error.response.data, null, 2));
      }
      return [];
    }
  }

  // Click2Call API - connects two numbers
  async click2Call(callerNumber, receiverNumber, callerId) {
    try {
      // MyOperator Click2Call endpoint
      const response = await axios.post(
        `${this.baseURL}/click2call`,
        {
          token: this.apiKey,
          caller: callerNumber,
          receiver: receiverNumber,
          caller_id: callerId || process.env.MYOPERATOR_NUMBER
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log(`✅ Click2Call initiated: ${callerNumber} → ${receiverNumber}`);
      return response.data;
    } catch (error) {
      console.error('Error in Click2Call:', error.response?.data || error.message);
      if (error.response) {
        console.error('Status:', error.response.status);
        console.error('Data:', JSON.stringify(error.response.data, null, 2));
      }
      throw error;
    }
  }

  // Batch call multiple candidates
  async batchCallCandidates(candidates, twilioNumber, myOperatorNumber) {
    const results = [];
    
    for (const candidate of candidates) {
      try {
        const result = await this.click2Call(
          candidate.phone,
          twilioNumber,
          myOperatorNumber
        );
        
        results.push({
          candidate_id: candidate.id,
          candidate_name: candidate.name,
          candidate_phone: candidate.phone,
          call_id: result.call_id,
          status: 'initiated'
        });
        
        // Small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 300));
        
      } catch (error) {
        console.error(`Failed to call candidate ${candidate.name}:`, error.message);
        results.push({
          candidate_id: candidate.id,
          candidate_name: candidate.name,
          status: 'failed',
          error: error.message
        });
      }
    }
    
    return results;
  }
}

module.exports = MyOperatorAPI;
