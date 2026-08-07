# ER Diagram v1

```mermaid
erDiagram
    users ||--o{ datasets : owns
    users ||--o{ label_tasks : creates
    datasets ||--o{ label_tasks : has
    datasets ||--o{ data_items : contains
    label_tasks ||--o{ data_items : contains
    data_items ||--o{ label_submissions : gets
    users ||--o{ label_submissions : submits

    users {
        int id PK
        string email UK
        string full_name
        string hashed_password
        enum role
        bool is_active
        datetime created_at
    }

    datasets {
        int id PK
        int owner_id FK
        string name
        text description
        string storage_url
        string file_type
        int total_items
        enum status
        datetime created_at
    }

    label_tasks {
        int id PK
        int dataset_id FK
        string title
        text instructions
        json label_schema
        int num_labelers
        bool ai_enabled
        enum status
        datetime created_at
    }

    data_items {
        int id PK
        int task_id FK
        int row_index
        json content_json
        json ai_suggestion
        float ai_confidence
        json final_label
        datetime created_at
    }

    label_submissions {
        int id PK
        int item_id FK
        int labeler_id FK
        json label_value
        string source
        datetime created_at
    }
```

## Notes

- `users.role` is one of `owner | labeler | admin`.
- A dataset belongs to one owner. Label tasks hang off a dataset; each dataset
  row becomes a `data_items` row per label task.
- Labelers submit labels through `label_submissions`, keyed to an item. Multiple
  labelers can label the same item (that's the `num_labelers` setting).
- `ai_suggestion` / `ai_confidence` on items feed the human-in-the-loop flow
  planned for later sprints.
