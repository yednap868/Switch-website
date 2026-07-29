# Community Feed - Complete Setup Guide

## What's Fixed

✅ **Posting** - Now fully functional, stores in `switch_community` collection  
✅ **Commenting** - Works end-to-end with proper error handling  
✅ **Liking** - Toggle like/unlike functionality  
✅ **Sharing** - Native share API with clipboard fallback  
✅ **Auto-Comments** - AI comments appear 2-3 minutes after user posts  
✅ **Anonymous Names** - Uses realistic Indian names (Amit, Suresh, etc.)  
✅ **Authentic Feel** - AI content doesn't feel generated

## Firestore Collection

All data is stored in: **`switch_community`**

Structure:
```
switch_community (collection)
├── {post_id} (document)
│   ├── user_id: string
│   ├── text: string
│   ├── author_name: string (anonymous name)
│   ├── is_anonymous: boolean
│   ├── is_ai_generated: boolean
│   ├── created_at: timestamp
│   ├── needs_ai_comments: boolean (flag for auto-comment service)
│   │
│   ├── likes (subcollection)
│   │   └── {like_id} (document)
│   │       ├── user_id: string
│   │       └── created_at: timestamp
│   │
│   └── comments (subcollection)
│       └── {comment_id} (document)
│           ├── user_id: string
│           ├── text: string
│           ├── author_name: string
│           ├── is_anonymous: boolean
│           ├── is_ai_generated: boolean
│           └── created_at: timestamp
```

## Auto-Comment Service Setup

The auto-comment service checks for new posts every minute and generates authentic AI comments 2-3 minutes after a user posts.

### Option 1: Run via Cron (Recommended)

Add to crontab to run every minute:

```bash
* * * * * cd /path/to/Vance-1 && /path/to/uv run python scripts/run_auto_comment.py >> /tmp/auto_comment.log 2>&1
```

### Option 2: Run via API Endpoint

Call this endpoint every minute (via external cron service or scheduled task):

```bash
curl -X POST http://localhost:8000/api/community/auto-comment
```

### Option 3: Run as Background Service

```bash
cd /Users/alt/Vance-1
uv run python scripts/run_auto_comment.py
```

## How It Works

1. **User Posts** → Post saved to `switch_community` with `needs_ai_comments: true`
2. **Auto-Comment Service** → Runs every minute, checks for posts 2-3 minutes old
3. **AI Comments Generated** → 2-3 authentic comments added automatically
4. **Likes Added** → 5-10 likes also added for engagement
5. **Flag Updated** → `needs_ai_comments` set to `false` to prevent duplicates

## Testing

1. **Post a rant** in the app
2. **Wait 2-3 minutes**
3. **Refresh the feed** - you should see AI comments appear
4. **Test liking** - click thumbs up, should toggle
5. **Test commenting** - add your own comment
6. **Test sharing** - click share button

## API Endpoints

- `GET /api/community/feed?user_id={user_id}` - Get feed
- `POST /api/community/post` - Create post
- `POST /api/community/post/{post_id}/like` - Like/unlike
- `POST /api/community/post/{post_id}/comment` - Add comment
- `POST /api/community/auto-comment` - Trigger auto-comment check

## Notes

- All posts/comments use anonymous names (Amit, Suresh, Mohan, etc.)
- AI comments feel authentic and natural
- Comments appear 2-3 minutes after posting
- Everything stored in `switch_community` collection
- All features fully functional end-to-end
