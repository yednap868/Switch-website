# Claude AI Prompts for Community Feed Content Generation

## Overview

These prompts are used by `community_ai_service.py` to generate realistic, engaging content for the Switch Community Feed. The goal is to create authentic-sounding rants and supportive engagement that feels natural and relatable to blue-collar/service workers in India.

## Rant Generation Prompt

**Purpose:** Generate realistic job/work-related rants

**Prompt Template:**
```
You are a member of the Switch job platform community. Generate a realistic, relatable rant about work, jobs, bosses, or career struggles.

Guidelines:
- Write in a casual, authentic voice (mix of Hindi-English Hinglish is fine)
- Keep it 50-150 words
- Make it relatable to blue-collar/service workers in India (delivery, retail, security, etc.)
- Include specific details (company names, situations, emotions)
- Should feel genuine, not overly dramatic
- Can be about: bad bosses, job search struggles, workplace issues, salary problems, work-life balance, etc.

Generate ONE rant that feels authentic and would resonate with job seekers and workers.
```

**Example Outputs:**
- "Boss ne aaj phir se late aane par taunt maara. 2 saal se same salary, aur abhi bhi respect nahi mil rahi. Kya karu?"
- "Job search me 3 mahine ho gaye. Har interview me 'experience chahiye' bolte hain, lekin experience kaise milega agar job hi nahi milegi?"
- "Delivery partner ki job me 12 ghante kaam karta hoon, phir bhi monthly target complete nahi hota. Family ko time hi nahi de pata."

## Comment Generation Prompt

**Purpose:** Generate supportive, engaging comments on existing posts

**Prompt Template:**
```
You are a supportive community member on Switch. Someone posted this rant:

"{post_text}"

Write a helpful, empathetic comment that:
- Shows you understand their situation
- Adds value (advice, encouragement, or shares a similar experience)
- Is 20-50 words
- Uses casual, friendly tone (Hinglish is fine)
- Offers support or shares your own story
- Feels genuine and not generic

Generate ONE comment that would be helpful and engaging.
```

**Example Outputs:**
- "Same situation mere saath bhi hua tha. Don't give up, better opportunity zarur milegi!"
- "Bhai, I understand. Keep trying, something will work out. All the best!"
- "Maine bhi yeh face kiya hai. Stay strong, better days ahead!"

## Content Seeding Strategy

### Daily Volume
- **100 posts per day** (distributed throughout 24 hours)
- **2-5 comments per post** (200-500 comments/day)
- **5-20 likes per post** (500-2000 likes/day)

### Timing Distribution
- Posts: Random timestamps in last 24 hours
- Comments: Within 1 hour of post creation
- Likes: Within 2 hours of post creation

### Topic Variety
- Bad bosses / management issues (30%)
- Job search struggles (25%)
- Salary / payment issues (20%)
- Work-life balance (15%)
- Workplace harassment / unfair treatment (10%)

### Engagement Patterns
- **Supportive Comments (60%)**: Empathy, encouragement, "same here" stories
- **Advice Comments (25%)**: Practical tips, suggestions
- **Helpful Comments (15%)**: Resource sharing, job leads, solutions

## Quality Guidelines

### Do's ✅
- Use Hinglish naturally (mix of Hindi and English)
- Include specific details (company names, locations, situations)
- Show genuine emotions (frustration, hope, determination)
- Keep it relatable to target audience
- Make engagement feel supportive and authentic

### Don'ts ❌
- Don't be overly dramatic or fake
- Don't use generic corporate language
- Don't make it sound like marketing copy
- Don't include personal information or real names
- Don't generate hateful or discriminatory content

## Fallback Content

If Claude API fails, the service uses pre-written fallback content that matches the style and tone. This ensures the feed always has content even if AI is unavailable.

## Monitoring & Optimization

- Track which topics get most engagement
- Monitor comment quality and relevance
- Adjust prompt based on user feedback
- A/B test different prompt variations
- Ensure diversity in generated content

## Usage

The prompts are called automatically by:
- `generate_rant()` - For creating posts
- `generate_engagement_comment()` - For creating comments
- `seed_community_content()` - For daily bulk seeding

These are integrated into the daily cron job that runs at 2 AM to seed 100 posts with engagement.
