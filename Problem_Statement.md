# Problem Statement: AI Dataset Labeling Marketplace

## 1. Title
AI Dataset Labeling Marketplace

## 2. Domain
Machine Learning / Data Annotation / Marketplace

## 3. Who is the user?
3 types of users:
- Dataset Owner - someone who has data (csv, json, images) and needs it labeled. Probably an ML student or dev.
- Labeler - whoever wants to make some cash or credits labeling data. Usually a student, freelancer, or bored ML person.
- Admin - runs the whole thing, kicks out bad actors, handles reports.

## 4. What problem we're solving
Getting labeled data is annoying. Like really annoying. You either pay Scale AI or Labelbox $$$ (like $1-3 per label), or you build some clunky spreadsheet system and ask your friends to do it for free. No middle ground.

A buddy of mine spent 3 months in his master's program manually labeling images because the university wouldn't pay for Scale AI credits. He could've finished his thesis 2 months early if there was a simple, cheap way to get decent labels.

We're building a marketplace: owners post tasks, labelers grab them, AI helps speed things up (auto-label + confidence score), and we use consensus (multiple people per item) to catch garbage labels. Everyone wins.

## 5. Proposed Solution
Web app, two sides:
- Backend: FastAPI (Python), PostgreSQL, because we're doing the Python track
- Frontend: React, because that's what everyone knows
- AI: OpenAI GPT API (primary), scikit-learn fallback for basic text stuff

Basic flow:
1. Owner uploads dataset (CSV/JSON for now, maybe images later)
2. Owner sets instructions, picks how many labelers per item, optionally turns on AI suggestions
3. Labelers browse tasks, claim one, start labeling
4. AI shows suggestions with confidence, labeler accepts/overrides
5. System tracks agreement between labelers, flags bad ones
6. Owner exports results when done

Storage: S3-compatible. But for dev we'll just use local files. No need to over-engineer Week 1.

## 6. Core Entities / Database Tables
1. users - email, name, password hash, role, active flag, timestamps
2. datasets - name, description, owner_id, file path, type, item count, status, timestamps
3. label_tasks - title, instructions, schema json, num_labelers, ai on/off, status, timestamps
4. data_items - the actual rows to label, with ai_suggestion + final_label as json
5. label_submissions - what each labeler submitted, linked to data_item + user
6. ai_suggestions - model predictions with confidence (not strictly necessary but mentioned in the spec)
7. task_claims - who claimed what (junction between label_tasks + labelers)

That's 7 tables. PDF says min 5. Done.

## 7. User Roles & Permissions
| Action | Owner | Labeler | Admin |
|---|---|---|---|
| Upload dataset | yes | no | maintenance |
| Create label task | yes | no | no |
| Claim task | no | yes | no |
| Submit labels | no | yes | no |
| Export results | yes | no | no |
| View all tasks | own only | no | yes |
| Ban/delete users | no | no | yes |

Roles are: "owner", "labeler", "admin". Stored as a string in the user record.

## 8. Success Criteria
- Upload a CSV + create a task in under 2 minutes
- Label 100 items in 10 min with AI on
- At least 2 core flows working by Day 11: owner posts task + labeler labels stuff

## 9. Out of Scope
- Payments (credit system only, no money changing hands)
- Images for now (text/tabular data first)
- Real-time collab (just claim a chunk and go)
- Mobile app (responsive web only)
- Fancy analytics dashboard (just export CSV/JSON)

## 10. Chosen Track
Python - FastAPI backend, SQLAlchemy, PostgreSQL 15
Frontend: React + Tailwind CSS
Testing: pytest
CI/CD: GitHub Actions
Hosting: Render (backend) + Vercel (frontend) later

---

## Week 1 Deliverables
- [x] Problem_Statement.md (this file)
- [x] GitHub repo created with branch protection
- [x] Boilerplate: .gitignore, LICENSE, .env.example
- [x] VS Code set up with extensions
- [x] Tech stack decided (Python/FastAPI)
- [x] Initial DB schema drafted (7 tables below)
- [x] Basic app structure created
- [x] Health check endpoint working
- [x] 3 commits across 2+ days

## DB Schema (Draft - Week 1)
```
users
  - id (PK)
  - email (unique)
  - full_name
  - hashed_password
  - role: owner/labeler/admin
  - is_active: boolean
  - created_at

datasets
  - id (PK)
  - owner_id (FK users)
  - name
  - description
  - storage_url
  - file_type
  - total_items
  - status: uploaded/processing/ready/failed
  - created_at

label_tasks
  - id (PK)
  - dataset_id (FK datasets)
  - title
  - instructions (text)
  - label_schema (JSON)
  - num_labelers
  - ai_enabled
  - status: draft/open/in_progress/completed
  - created_at

data_items
  - id (PK)
  - task_id (FK label_tasks)
  - row_index (int)
  - content_json (JSON)
  - ai_suggestion (JSON or null)
  - ai_confidence (float)
  - final_label (JSON or null)
  - created_at

label_submissions
  - id (PK)
  - item_id (FK data_items)
  - labeler_id (FK users)
  - label_value (JSON)
  - source: human/ai_accepted/ai_override
  - created_at

task_claims
  - id (PK)
  - task_id (FK label_tasks)
  - labeler_id (FK users)
  - assigned_count (int)
  - status: available/claimed/submitted
  - claimed_at
  - completed_at

ai_suggestions
  - id (PK)
  - item_id (FK data_items)
  - model_name
  - confidence_score
  - prediction_json (JSON)
  - created_at
```
