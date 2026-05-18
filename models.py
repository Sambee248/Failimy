from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    families = db.relationship('Family', backref='owner', lazy='dynamic',
                               cascade='all, delete-orphan')
    members_created = db.relationship('Member', backref='creator', lazy='dynamic',
                                      foreign_keys='Member.created_by')

class Family(db.Model):
    __tablename__ = 'families'
    family_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    family_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship('Member', backref='family', lazy='dynamic',
                              cascade='all, delete-orphan')

class Member(db.Model):
    __tablename__ = 'members'
    member_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.family_id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    gender = db.Column(db.String(1), nullable=False, index=True)
    birth_date = db.Column(db.Date, nullable=True, index=True)
    death_date = db.Column(db.Date, nullable=True)
    generation = db.Column(db.Integer, default=1, index=True)
    biography = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("gender IN ('M', 'F')", name='ck_member_gender'),
        db.CheckConstraint("death_date IS NULL OR birth_date IS NULL OR death_date >= birth_date",
                          name='ck_member_dates'),
    )

class FamilyRelation(db.Model):
    __tablename__ = 'family_relations'
    relation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('members.member_id'), nullable=False, index=True)
    child_id = db.Column(db.Integer, db.ForeignKey('members.member_id'), nullable=False, index=True)
    relation_type = db.Column(db.String(20), default='biological')

    parent = db.relationship('Member', foreign_keys=[parent_id], backref='children_relations')
    child = db.relationship('Member', foreign_keys=[child_id], backref='parent_relations')

    __table_args__ = (
        db.CheckConstraint("relation_type IN ('biological', 'adopted')", name='ck_relation_type'),
        db.CheckConstraint('parent_id != child_id', name='ck_not_self_parent'),
        db.UniqueConstraint('parent_id', 'child_id', name='uq_parent_child'),
    )

class Marriage(db.Model):
    __tablename__ = 'marriages'
    marriage_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    husband_id = db.Column(db.Integer, db.ForeignKey('members.member_id'), nullable=False, index=True)
    wife_id = db.Column(db.Integer, db.ForeignKey('members.member_id'), nullable=False, index=True)
    marriage_date = db.Column(db.Date, nullable=True)
    divorce_date = db.Column(db.Date, nullable=True)

    husband = db.relationship('Member', foreign_keys=[husband_id], backref='marriages_as_husband')
    wife = db.relationship('Member', foreign_keys=[wife_id], backref='marriages_as_wife')

    __table_args__ = (
        db.CheckConstraint('husband_id != wife_id', name='ck_not_self_marriage'),
        db.CheckConstraint("divorce_date IS NULL OR marriage_date IS NULL OR divorce_date >= marriage_date",
                          name='ck_marriage_dates'),
    )
