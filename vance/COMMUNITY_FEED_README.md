# Community Feed Feature - AI-Powered Content Seeding

## Overview

The Community Feed is an anonymous rant/engagement platform where users can:
- Post anonymous rants about jobs, bosses, work life
- Like and comment on posts
- Get support from the community
- See AI-generated content for engagement

## Architecture

### Frontend (`Switch-app/src/SwitchApp.jsx`)
- **New Tab**: "Community" in bottom navigation
- **Components**:
  - Feed view with posts, likes, comments
  - Post rant modal
  - Comments modal
- **State**: `communityPosts`, `newRantText`, `selectedPost`, `commentText`

### Backend (`api/community_routes.py`)
- `GET /api/community/feed` - Get feed posts
- `POST /api/community/post` - Create new post
- `POST /api/community/post/{post_id}/like` - Like/unlike post
- `POST /api/community/post/{post_id}/comment` - Add comment

### AI Service (`services/community_ai_service.py`)
- `generate_rant()` - Uses Claude to generate realistic rants
- `generate_engagement_comment()` - Generates helpful comments
- `seed_community_content()` - Seeds 100 posts/day with engagement

### Firestore Schema

```
community_posts (collection)
├── {post_id} (document)
│   ├── user_id: string
│   ├── text: string
│   ├── author_name: string (or null if anonymous)
│   ├── is_anonymous: boolean
│   ├── is_ai_generated: boolean
│   ├── created_at: timestamp
│   │
│   ├── likes (subcollection)
│   │   └── {user_id} (document)
│   │       ├── user_id: string
│   │       └── created_at: timestamp
│   │
│   └── comments (subcollection)
│       └── {comment_id} (document)
│           ├── user_id: string
│           ├── text: string
│           ├── author_name: string (or null)
│           ├── is_anonymous: boolean
│           ├── is_ai_generated: boolean
│           └── created_at: timestamp
```

## AI Content Generation

### Claude Prompts

**Rant Generation:**
- Casual, authentic voice (Hinglish OK)
- 50-150 words
- Relatable to blue-collar/service workers
- Topics: bad bosses, job search, workplace issues, salary, work-life balance

**Comment Generation:**
- Empathetic, supportive
- 20-50 words
- Adds value (advice, encouragement, shares experience)
- Offers help or shares similar story

### Content Seeding Strategy

**Daily Target: 100 posts**
- Each post gets 2-5 comments
- Each post gets 5-20 likes
- Posts distributed throughout the day (timestamps in last 24h)
- Comments appear within 1 hour of post
- Likes appear within 2 hours of post

## Setup & Usage

### 1. Run Seeding Script (Daily)

```bash
# Manual run
cd /Users/alt/Vance-1
uv run python scripts/seed_community_feed.py

# Or via API (for testing)
curl -X POST https://api.relayy.world/api/community/seed?posts_per_day=10
```

### 2. Set Up Cron Job (Production)

Add to crontab to run daily at 2 AM:

```bash
0 2 * * * cd /path/to/Vance-1 && /path/to/uv run python scripts/seed_community_feed.py >> /tmp/community_seed.log 2>&1
```

### 3. Frontend Usage

Users can:
1. Click "Community" tab in bottom nav
2. Click "Post" button to create rant
3. Like posts by clicking thumbs up
4. View/add comments by clicking comment icon
5. All posts are anonymous by default

## API Endpoints

### Get Feed
```bash
GET /api/community/feed?user_id=918368828660
```

### Post Rant
```bash
POST /api/community/post
{
  "user_id": "918368828660",
  "text": "My boss is so unfair...",
  "is_anonymous": true
}
```

### Like Post
```bash
POST /api/community/post/{post_id}/like
{
  "user_id": "918368828660"
}
```

### Add Comment
```bash
POST /api/community/post/{post_id}/comment
{
  "user_id": "918368828660",
  "text": "I understand your situation...",
  "is_anonymous": true
}
```

## UI Features

- **Consistent Design**: Matches Switch app's emerald/teal gradient theme
- **Anonymous Avatars**: Generic colored circles with initials
- **Engagement Metrics**: Like count, comment count visible
- **Real-time Updates**: Feed refreshes after posting/liking/commenting
- **Mobile-First**: Optimized for mobile screens

## Content Farming Strategy

1. **Daily Seeding**: 100 AI posts/day keeps feed active
2. **Engagement**: Each post gets comments and likes automatically
3. **Realistic Timing**: Posts/comments/likes have realistic timestamps
4. **Variety**: AI generates diverse topics and styles
5. **Natural Feel**: Mix of AI and real user content

## Monitoring

Check seeding logs:
```bash
tail -f /tmp/community_seed.log
```

Check Firestore:
- Go to Firebase Console → Firestore
- View `community_posts` collection
- Check `is_ai_generated` field to distinguish AI vs real posts

## Notes

- All posts are anonymous by default
- AI-generated posts marked with `is_ai_generated: true`
- Real user posts have `is_ai_generated: false`
- Feed sorted by engagement (likes + comments * 2) and recency
- Claude API key required in `ANTHROPIC_API_KEY` env var
