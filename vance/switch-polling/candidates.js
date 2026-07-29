// In-memory candidate storage for MVP
// Replace with database later

const candidates = [
  {
    id: '1',
    name: 'Rajesh Kumar',
    phone: '+919876543210',
    job_type: 'security_guard',
    location: 'udyog_vihar',
    experience: 3,
    call_ready: true
  },
  {
    id: '2',
    name: 'Amit Singh',
    phone: '+919876543211',
    job_type: 'security_guard',
    location: 'cyber_hub',
    experience: 5,
    call_ready: true
  },
  {
    id: '3',
    name: 'Suresh Yadav',
    phone: '+919876543212',
    job_type: 'delivery_partner',
    location: 'sector_46',
    experience: 2,
    call_ready: true
  },
  {
    id: '4',
    name: 'Priya Sharma',
    phone: '+919876543213',
    job_type: 'warehouse_worker',
    location: 'udyog_vihar',
    experience: 1,
    call_ready: true
  },
  {
    id: '5',
    name: 'Ravi Verma',
    phone: '+919876543214',
    job_type: 'security_guard',
    location: 'sector_46',
    experience: 4,
    call_ready: true
  },
];

function findMatchingCandidates(requirements) {
  const { job_type, location, experience } = requirements;
  
  return candidates.filter(candidate => {
    // Match job type
    if (job_type && candidate.job_type !== job_type.toLowerCase().replace(/\s+/g, '_')) {
      return false;
    }
    
    // Match location (fuzzy match)
    if (location) {
      const normalizedLocation = location.toLowerCase().replace(/\s+/g, '_');
      if (!candidate.location.includes(normalizedLocation) && 
          !normalizedLocation.includes(candidate.location)) {
        return false;
      }
    }
    
    // Match experience (candidate should have >= required)
    if (experience && candidate.experience < parseInt(experience)) {
      return false;
    }
    
    // Must be call-ready
    if (!candidate.call_ready) {
      return false;
    }
    
    return true;
  }).sort((a, b) => b.experience - a.experience); // Sort by experience (best first)
}

function getCandidateById(id) {
  return candidates.find(c => c.id === id);
}

function getCandidateByPhone(phone) {
  return candidates.find(c => c.phone === phone);
}

module.exports = { 
  findMatchingCandidates, 
  getCandidateById,
  getCandidateByPhone,
  candidates 
};
