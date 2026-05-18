-- PostgreSQL Reference Schema for Family Genealogy System
-- Usage: psql -U your_user -d your_db -f schema.sql

CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE families (
    family_id       SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    family_name     VARCHAR(100) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, family_name)
);

CREATE TABLE members (
    member_id       SERIAL PRIMARY KEY,
    family_id       INTEGER NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    gender          CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    birth_date      DATE,
    death_date      DATE,
    generation      INTEGER DEFAULT 1,
    biography       TEXT,
    created_by      INTEGER REFERENCES users(user_id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (death_date IS NULL OR birth_date IS NULL OR death_date >= birth_date)
);

CREATE TABLE family_relations (
    relation_id     SERIAL PRIMARY KEY,
    parent_id       INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    child_id        INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    relation_type   VARCHAR(20) DEFAULT 'biological'
        CHECK (relation_type IN ('biological', 'adopted')),
    UNIQUE(parent_id, child_id),
    CHECK (parent_id != child_id)
);

CREATE TABLE marriages (
    marriage_id     SERIAL PRIMARY KEY,
    husband_id      INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    wife_id         INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    marriage_date   DATE,
    divorce_date    DATE,
    CHECK (husband_id != wife_id),
    CHECK (divorce_date IS NULL OR marriage_date IS NULL OR divorce_date >= marriage_date)
);

-- Indexes for query performance
CREATE INDEX idx_member_family ON members(family_id);
CREATE INDEX idx_member_name ON members(name);
CREATE INDEX idx_member_gender ON members(gender);
CREATE INDEX idx_member_birth ON members(birth_date);
CREATE INDEX idx_member_generation ON members(generation);
CREATE INDEX idx_relation_parent ON family_relations(parent_id);
CREATE INDEX idx_relation_child ON family_relations(child_id);
CREATE INDEX idx_marriage_husband ON marriages(husband_id);
CREATE INDEX idx_marriage_wife ON marriages(wife_id);

-- Prevent cyclic parent-child relations
CREATE OR REPLACE FUNCTION check_cycle_relation()
RETURNS TRIGGER AS $$
DECLARE
    found_self BOOLEAN;
BEGIN
    WITH RECURSIVE ancestor_chain AS (
        SELECT parent_id, child_id, 1 AS depth
        FROM family_relations
        WHERE child_id = NEW.parent_id

        UNION ALL

        SELECT fr.parent_id, fr.child_id, ac.depth + 1
        FROM family_relations fr
        JOIN ancestor_chain ac ON fr.child_id = ac.parent_id
        WHERE ac.depth < 100
    )
    SELECT EXISTS (
        SELECT 1 FROM ancestor_chain WHERE parent_id = NEW.child_id
    ) INTO found_self;

    IF found_self THEN
        RAISE EXCEPTION 'Cyclic relation detected';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_cycle
    BEFORE INSERT ON family_relations
    FOR EACH ROW
    EXECUTE FUNCTION check_cycle_relation();


-- Enforce parent birth date < child birth date
CREATE OR REPLACE FUNCTION check_parent_birth_before_child()
RETURNS TRIGGER AS $$
DECLARE
    parent_birth DATE;
    child_birth  DATE;
BEGIN
    SELECT birth_date INTO parent_birth FROM members WHERE member_id = NEW.parent_id;
    SELECT birth_date INTO child_birth  FROM members WHERE member_id = NEW.child_id;

    IF parent_birth IS NOT NULL AND child_birth IS NOT NULL
       AND parent_birth >= child_birth THEN
        RAISE EXCEPTION 'Parent birth date (%) must be before child birth date (%)',
            parent_birth, child_birth;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_parent_birth_before_child
    BEFORE INSERT ON family_relations
    FOR EACH ROW
    EXECUTE FUNCTION check_parent_birth_before_child();
