# Vance - AI Networking Agent Product Overview

## 🎯 What is Vance?

**Vance** is an AI-powered networking agent that connects professionals through intelligent introductions. Operating primarily via **WhatsApp**, Vance uses advanced AI (Claude 3.7 Sonnet) to understand user needs, match professionals, and facilitate meaningful connections between job seekers, founders, recruiters, and other professionals.

---

## 🚀 Core Features

### 1. **Multi-Modal Communication**
- **WhatsApp Text Mode**: Primary interface for quick, conversational interactions
- **Voice Calls (ElevenLabs)**: Deep-dive conversations to understand user needs, goals, and requirements
- **Email Workflows**: Formal introduction emails when users want to connect

### 2. **Intelligent User Onboarding**

#### Text-Based Onboarding (WhatsApp)
For new users, Vance collects essential information in a structured flow:
1. **Connection Type**: "What kind of people are you looking to connect with?"
   - Candidates might say: "founders hiring engineers", "recruiters", "tech companies"
   - Hiring founders might say: "software engineers", "full stack developers", "candidates"
2. **Name**: "What should I call you?"
3. **Email**: "What's your email? I'll send you some connections."
4. **LinkedIn**: "Send me your LinkedIn - I want to see your background before we talk."

After collecting these basics, Vance offers a voice call for deeper understanding.

#### Voice Call Onboarding
- **5-minute deep-dive conversations** to understand:
  - User's story and background
  - Current focus and priorities
  - Urgent needs and goals
  - Specific requirements (for job providers: role, skills, experience level, etc.)
  - For job seekers: target role, skills, location preferences, etc.
- **Automatic extraction** of structured data from natural conversation
- **Memory across calls** - Vance remembers previous conversations and builds on them

### 3. **User Classification & Intent Detection**

Vance automatically classifies users into:
- **Job Seekers**: Looking for opportunities, roles, connections
- **Job Providers**: Hiring founders, recruiters looking for talent
- **General Users**: Networking, partnerships, other needs

The system uses AI to detect intent from conversations and extraction data.

### 4. **Intelligent Profile Matching**

#### Hybrid Matching System
Vance uses a sophisticated multi-stage matching process:

1. **Hard Filters**: Intent-based filtering (job seeker vs. job provider)
2. **Vector Search (Qdrant)**: Semantic similarity matching using embeddings
3. **AI Reranking (Claude)**: Intelligent scoring and relevance assessment
4. **Final Selection**: Top 3 most relevant matches

#### Matching Criteria
- **For Job Providers**: Matches candidates based on:
  - Required skills and technologies
  - Experience level
  - Location preferences
  - Work model (remote/hybrid/on-site)
  - Cultural fit and background

- **For Job Seekers**: Matches opportunities based on:
  - Target role and skills
  - Location preferences
  - Company stage and culture
  - Work model preferences

### 5. **Automatic Onboarding Broadcasts**

When a new user completes text onboarding (connection type + name + email + LinkedIn), Vance automatically:
- Identifies the right audience (founders, recruiters, candidates, etc.)
- Sends a short, human-style WhatsApp message to relevant people:
  > "I just spoke with {Name} — they're looking to connect with {connection_type}.\nNeed an intro?"

**Smart Features:**
- Uses template messages for broadcasts sent >24 hours after onboarding (WhatsApp policy compliance)
- Saves broadcast context to conversation history for response handling
- Differentiated response handling:
  - **Job Providers** responding "I need intro" → Go directly to scheduling
  - **Candidates** responding "I need intro" → Notify the other party and wait for approval

### 6. **Profile Suggestions & Candidate Presentation**

After voice calls, Vance:
- **Decides** (using Claude AI) whether to send candidate profiles based on:
  - User's hiring intent
  - Profile quality and relevance
  - User's engagement history
- **Finds matches** using hybrid search
- **Presents top 3 candidates** with:
  - Name and LinkedIn profile
  - Match reason (why they're a good fit)
  - Key skills and background
  - Public profile link (profiles.vance.so)

### 7. **Interview Scheduling**

Vance enables direct interview scheduling via WhatsApp:

**Flow:**
1. Job provider reviews candidate profiles
2. Says "I want to talk to [candidate name]" or "I'd like to interview candidate 2"
3. Vance asks: "When works for you? (e.g., 'tomorrow 2pm' or 'Monday 10am')"
4. User provides time preference
5. Vance creates calendar events (Google Calendar integration)
6. Sends calendar invites to both parties
7. Notifies candidate about the scheduled interview

**Features:**
- Natural language time parsing ("tomorrow 2pm", "next Monday 10am")
- Google Calendar integration
- Automatic notifications to both parties
- Timezone handling

### 8. **Public Candidate Profiles**

Vance creates public profiles for job seekers at `profiles.vance.so/{slug}`:

**Profile Features:**
- **Basic Info**: Name, role, experience, location, LinkedIn
- **High-Signal Content** (AI-generated):
  - **Story**: Personal and professional journey
  - **Strengths**: Key skills, projects, motivations
  - **Proof of Work**: Demonstrated achievements
  - **Thoughts**: Insights and perspectives
- **Audio Clips**:
  - **Intro Audio**: Short introduction from voice call
  - **Thinking Audio**: Deep-dive thoughts from conversation
- **Verification Badge**: "100% verified through Vance card" (Top 6%)
- **Activity Metrics**: Introductions count, interviews scheduled, response time
- **Opportunities Section**: Role preferences, industries, company stage

**Audio Handling:**
- Fetches audio from ElevenLabs call recordings
- Stores as base64 data URLs (for small files) or conversation IDs (for large files)
- On-demand audio fetching via API endpoint for large files
- CORS-enabled for frontend playback

### 9. **Email Introduction Workflow**

When users want to connect:
1. User says "I want to connect with [name]"
2. Vance collects consent and additional details
3. Sends formal introduction email via Gmail
4. Includes both parties' information and context
5. Tracks email delivery and responses

### 10. **Founder Referral System**

After successful interactions (profiles sent, interviews scheduled, hires made), Vance:
- Sends referral prompts to founders
- Provides personalized referral links: `https://wa.me/12183180007?text=Hi%20Vance%2C%20{founder_name}%20sent%20me`
- Tracks referrals and attributes new signups
- Idempotent (max once per 7 days per founder)

### 11. **Conversation Memory & Context**

Vance maintains comprehensive memory:
- **User Profiles**: Name, email, LinkedIn, goals, preferences
- **Extraction Data**: Structured data from voice calls
- **Conversation History**: All WhatsApp messages and context
- **Call Transcripts**: Full voice call transcripts stored
- **State Management**: Conversation state persists across sessions
- **Multi-Call Memory**: Remembers previous calls and builds on them

### 12. **Admin Dashboard**

Web-based admin interface for:
- Manual profile sending
- User search and management
- Profile history tracking
- Sending statistics

---

## 🔧 Technical Architecture

### Core Technologies
- **Backend**: FastAPI, Python 3.11+, Uvicorn
- **AI/LLM**: Claude 3.7 Sonnet (primary), OpenAI/Mistral/Cohere (fallbacks)
- **Databases**: 
  - Firestore (primary data store)
  - Qdrant (vector database for semantic search)
  - Redis (caching, deduplication)
- **APIs**: 
  - WhatsApp Business API
  - ElevenLabs (voice calls)
  - Gmail API (email introductions)
  - Google Calendar API (scheduling)
  - ScrapingDog (LinkedIn scraping)
- **Package Manager**: UV (Rust-based)

### Key Services

| Service | Purpose |
|--------|---------|
| `conversation_service.py` | Conversation flow orchestration, state machine, user classification |
| `claude_profile_service.py` | Claude-powered profile matching and suggestions |
| `claude_onboarding_service.py` | AI-driven user onboarding |
| `voice_extraction_service.py` | Intelligent field extraction from voice calls |
| `hybrid_matching_service.py` | Multi-stage profile matching (filters + vector + AI) |
| `interview_scheduling_service.py` | Calendar integration and interview scheduling |
| `onboarding_broadcast_service.py` | Automatic broadcast messages for new users |
| `post_call_workflow.py` | Post-call processing orchestration |
| `founder_referral_service.py` | Referral link generation and tracking |
| `profile_audio_service.py` | Audio attachment to public profiles |
| `email_service.py` | Email workflow management |

### Data Flow

1. **User sends WhatsApp message** → Webhook handler
2. **State check** → Load user profile, extraction data, conversation history
3. **AI processing** → Claude AI determines response and actions
4. **Tool execution** → Profile matching, scheduling, data logging, etc.
5. **Response** → WhatsApp message sent to user
6. **Data persistence** → Firestore, Qdrant, conversation history updated

---

## 📊 User Flows

### Flow 1: New Job Seeker Onboarding
```
1. User texts Vance on WhatsApp
2. Vance asks: "What kind of people are you looking to connect with?"
3. User: "founders hiring engineers"
4. Vance collects: name, email, LinkedIn
5. Vance offers voice call
6. Voice call: Deep dive into skills, experience, goals
7. Extraction: Structured data saved
8. Broadcast: Message sent to relevant job providers
9. Profile created: Public profile at profiles.vance.so/{slug}
10. Matching: When job providers need candidates, Vance suggests this profile
```

### Flow 2: New Job Provider Onboarding
```
1. User texts Vance on WhatsApp
2. Vance asks: "What kind of people are you looking to connect with?"
3. User: "full stack engineers"
4. Vance collects: name, email, LinkedIn
5. Voice call: Discuss hiring needs, role requirements, team culture
6. Extraction: Structured data saved (job_title, required_skills, etc.)
7. Broadcast: Message sent to relevant candidates
8. Post-call: Vance finds matching candidates and sends profiles
9. User selects candidate: "I want to talk to candidate 2"
10. Scheduling: Interview scheduled via WhatsApp
11. Calendar invites sent to both parties
```

### Flow 3: Profile Matching & Introduction
```
1. Job provider asks: "Show me some candidates"
2. Vance searches Qdrant for matches
3. AI reranks results
4. Top 3 candidates presented with match reasons
5. User: "I want to connect with John"
6. Vance collects consent and details
7. Introduction email sent via Gmail
8. Both parties notified
```

### Flow 4: Broadcast Response
```
1. Candidate receives broadcast: "I just spoke with Saurabh — they're looking to connect with full stack engineers. Need an intro?"
2. Candidate: "I need intro"
3. Vance notifies job provider: "{candidate_name} wants to connect with you, should I schedule a call?"
4. Job provider: "Yes"
5. Scheduling flow initiated
```

---

## 🎨 Key Differentiators

1. **Conversational AI**: Natural, human-like interactions via WhatsApp
2. **Multi-Modal**: Text + Voice for comprehensive understanding
3. **Intelligent Matching**: AI-powered, not just keyword-based
4. **Automated Workflows**: From onboarding to scheduling, minimal manual intervention
5. **Public Profiles**: Rich, verified candidate profiles with audio
6. **Context-Aware**: Remembers previous conversations and builds on them
7. **Fast Response**: Real-time WhatsApp interactions
8. **Scalable**: Handles multiple users concurrently

---

## 📈 Current Statistics

- **Total Users**: 114
- **Job Seekers**: 29
- **Job Providers**: 3
- **Unclassified**: 82 (15 with potential hiring intent)

---

## 🔐 Security & Privacy

- Firebase authentication and secure data storage
- WhatsApp Business API compliance
- GDPR-ready data handling
- Secure API keys management via environment variables
- Admin dashboard authentication

---

## 🚀 Future Enhancements

- Enhanced matching algorithms
- More integration options (Slack, Teams, etc.)
- Advanced analytics and insights
- Mobile app
- Group introductions
- Automated follow-ups
- Success tracking and metrics

---

## 📞 Support & Documentation

- **API Documentation**: `http://localhost:8000/api/docs` (Swagger UI)
- **Admin Dashboard**: `http://localhost:5001/admin`
- **Public Profiles**: `https://profiles.vance.so/{slug}`

---

*Last Updated: Based on current codebase analysis*

