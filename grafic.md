```mermaid
erDiagram
    %% 先声明关系，利用层级引导渲染引擎生成上下紧凑结构
    users ||--o{ families : "创建"
    users ||--o{ members : "录入"
    families ||--o{ members : "包含"
    members ||--o{ family_relations : "父代与子代"
    members ||--o{ marriages : "丈夫与妻子"

    %% 后声明表结构
    users {
        int user_id PK
        varchar username
        varchar password_hash
        varchar email
    }
    families {
        int family_id PK
        int user_id FK
        varchar family_name
        text description
    }
    members {
        int member_id PK
        int family_id FK
        varchar name
        char gender
        date birth_date
        int generation
    }
    family_relations {
        int relation_id PK
        int parent_id FK
        int child_id FK
        varchar relation_type
    }
    marriages {
        int marriage_id PK
        int husband_id FK
        int wife_id FK
        date marriage_date
    }
