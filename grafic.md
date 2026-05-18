```mermaid
erDiagram
    users {
        int user_id PK "用户ID"
        varchar username "用户名"
        varchar password_hash "密码哈希"
        varchar email "邮箱"
        timestamp created_at "创建时间"
    }
    families {
        int family_id PK "家族ID"
        int user_id FK "创建者ID"
        varchar family_name "家族名称"
        text description "家族描述"
        timestamp created_at "创建时间"
    }
    members {
        int member_id PK "成员ID"
        int family_id FK "所属家族ID"
        varchar name "姓名"
        char gender "性别"
        date birth_date "出生日期"
        date death_date "死亡日期"
        int generation "世代"
        text biography "传记/简介"
        int created_by FK "录入用户ID"
        timestamp created_at "创建时间"
    }
    family_relations {
        int relation_id PK "关系ID"
        int parent_id FK "父代成员ID"
        int child_id FK "子代成员ID"
        varchar relation_type "关系类型(亲生/收养)"
    }
    marriages {
        int marriage_id PK "婚姻ID"
        int husband_id FK "丈夫成员ID"
        int wife_id FK "妻子成员ID"
        date marriage_date "结婚日期"
        date divorce_date "离婚日期"
    }

    %% 实体关系连线
    users ||--o{ families : "创建 (1:N)"
    users ||--o{ members : "录入 (1:N)"
    families ||--o{ members : "包含 (1:N)"
    members ||--o{ family_relations : "作为父代 (1:N)"
    members ||--o{ family_relations : "作为子代 (1:N)"
    members ||--o{ marriages : "作为丈夫 (1:N)"
    members ||--o{ marriages : "作为妻子 (1:N)"
