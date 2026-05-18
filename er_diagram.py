"""Generate ER diagram as PlantUML (.puml) and Mermaid (.mmd) text for the genealogy database."""

ER_PLANTUML = """
@startuml genealogy_er
!theme plain
skinparam backgroundColor #FFFFFF
skinparam roundCorner 10

entity "users" as users {
  * user_id : INTEGER <<PK>>
  --
  * username : VARCHAR(50) <<UNIQUE, INDEX>>
  * password_hash : VARCHAR(255)
  email : VARCHAR(100)
  created_at : DATETIME
}

entity "families" as families {
  * family_id : INTEGER <<PK>>
  --
  * user_id : INTEGER <<FK, INDEX>>
  * family_name : VARCHAR(100)
  description : TEXT
  created_at : DATETIME
}

entity "members" as members {
  * member_id : INTEGER <<PK>>
  --
  * family_id : INTEGER <<FK, INDEX>>
  * name : VARCHAR(100) <<INDEX>>
  * gender : CHAR(1) <<INDEX, CHECK(M/F)>>
  birth_date : DATE <<INDEX>>
  death_date : DATE
  * generation : INTEGER <<INDEX>>
  biography : TEXT
  created_by : INTEGER <<FK>>
  created_at : DATETIME
}

entity "family_relations" as family_relations {
  * relation_id : INTEGER <<PK>>
  --
  * parent_id : INTEGER <<FK, INDEX>>
  * child_id : INTEGER <<FK, INDEX>>
  relation_type : VARCHAR(20) <<CHECK(biological/adopted)>>
  ==
  UNIQUE(parent_id, child_id)
  CHECK(parent_id != child_id)
}

entity "marriages" as marriages {
  * marriage_id : INTEGER <<PK>>
  --
  * husband_id : INTEGER <<FK, INDEX>>
  * wife_id : INTEGER <<FK, INDEX>>
  marriage_date : DATE
  divorce_date : DATE
  ==
  CHECK(husband_id != wife_id)
  CHECK(divorce >= marriage)
}

users ||--o{ families : "owns"
families ||--o{ members : "contains"
members ||--o{ family_relations : "as parent (parent_id)"
members ||--o{ family_relations : "as child (child_id)"
members ||--o{ marriages : "as husband"
members ||--o{ marriages : "as wife"
users ||--o{ members : "creates"

note right of family_relations
  Recursive self-referencing
  via members table
  Cycle prevention trigger
  in schema.sql
end note

note right of members
  CHECK: death_date >= birth_date
  CHECK: gender IN ('M','F')
  Parent birth < child birth
  validated in app layer
end note

@enduml
"""

ER_MERMAID = """
erDiagram
    users {
        int user_id PK
        varchar username UK "unique, indexed"
        varchar password_hash
        varchar email
        datetime created_at
    }

    families {
        int family_id PK
        int user_id FK "indexed, →users"
        varchar family_name
        text description
        datetime created_at
    }

    members {
        int member_id PK
        int family_id FK "indexed, →families"
        varchar name "indexed"
        char gender "indexed, CHECK(M/F)"
        date birth_date "indexed"
        date death_date
        int generation "indexed"
        text biography
        int created_by FK "→users"
        datetime created_at
    }

    family_relations {
        int relation_id PK
        int parent_id FK "indexed, →members"
        int child_id FK "indexed, →members"
        varchar relation_type "CHECK(biological/adopted)"
    }

    marriages {
        int marriage_id PK
        int husband_id FK "indexed, →members"
        int wife_id FK "indexed, →members"
        date marriage_date
        date divorce_date
    }

    users ||--o{ families : owns
    families ||--o{ members : contains
    users ||--o{ members : creates
    members ||--o{ family_relations : "as parent"
    members ||--o{ family_relations : "as child"
    members ||--o{ marriages : "as husband"
    members ||--o{ marriages : "as wife"
"""

RELATION_SCHEMA = """
Relation Schema (3NF Analysis)
===============================

Table: users
  user_id → username, password_hash, email, created_at
  (All non-key attributes depend on the whole key user_id)

Table: families
  family_id → user_id, family_name, description, created_at
  (user_id is FK to users; all attributes depend on family_id)

Table: members
  member_id → family_id, name, gender, birth_date, death_date,
              generation, biography, created_by, created_at
  (family_id FK to families; created_by FK to users)
  * generation is NOT transitively dependent — it's a direct attribute
  * No 3NF violations

Table: family_relations
  relation_id → parent_id, child_id, relation_type
  (parent_id, child_id both FK to members)

Table: marriages
  marriage_id → husband_id, wife_id, marriage_date, divorce_date
  (husband_id, wife_id both FK to members)

All tables satisfy 3NF:
  - Each table has a single-purpose primary key
  - No repeating groups (1NF)
  - No partial dependencies (2NF — all keys are single-column)
  - No transitive dependencies (3NF — non-key attributes don't depend on other non-key attributes)
"""

if __name__ == '__main__':
    with open('er_diagram.puml', 'w', encoding='utf-8') as f:
        f.write(ER_PLANTUML)
    print("PlantUML ER diagram saved to: er_diagram.puml")

    with open('er_diagram.mmd', 'w', encoding='utf-8') as f:
        f.write(ER_MERMAID)
    print("Mermaid ER diagram saved to: er_diagram.mmd")

    with open('relation_schema.txt', 'w', encoding='utf-8') as f:
        f.write(RELATION_SCHEMA)
    print("Relation schema (3NF analysis) saved to: relation_schema.txt")

    print("\nDone! Use https://www.plantuml.com/ or https://mermaid.live/ to render.")
    print("Or render locally: java -jar plantuml.jar er_diagram.puml")
