# -*- coding: utf-8 -*-
"""Verify the generated data meets all requirements."""
from app import create_app
from models import db, User, Family, Member
from sqlalchemy import func

app = create_app()
with app.app_context():
    users = User.query.count()
    families = Family.query.count()
    total_members = Member.query.count()

    print(f"Users: {users}")
    print(f"Families: {families}")
    print(f"Total members: {total_members}")

    # Per-family stats
    print(f"\n{'Family':<20} {'User':<10} {'Members':>8} {'Gens':>6}")
    print("-" * 50)
    for fam in Family.query.order_by(Family.family_id).all():
        mem_count = Member.query.filter_by(family_id=fam.family_id).count()
        max_gen = db.session.query(func.max(Member.generation)).filter_by(family_id=fam.family_id).scalar() or 0
        user = User.query.get(fam.user_id)
        print(f"{fam.family_name:<20} {user.username:<10} {mem_count:>8} {max_gen:>6}")

    # Largest family
    largest = Family.query.outerjoin(Member).group_by(Family.family_id).order_by(func.count(Member.member_id).desc()).first()
    if largest:
        mc = Member.query.filter_by(family_id=largest.family_id).count()
        print(f"\nLargest family: {largest.family_name} with {mc} members")

    # Check: every member has at least one relation
    from models import FamilyRelation, Marriage
    members_without_relations = Member.query.filter(
        ~Member.member_id.in_(
            db.session.query(FamilyRelation.child_id).union(
                db.session.query(FamilyRelation.parent_id)
            ).union(
                db.session.query(Marriage.husband_id)
            ).union(
                db.session.query(Marriage.wife_id)
            )
        )
    ).count()
    print(f"\nMembers without any relationship: {members_without_relations}")

    # Requirements
    print(f"\nRequirements:")
    print(f"  Users >= 10: {'PASS' if users >= 10 else 'FAIL'} ({users})")
    print(f"  Families >= 10: {'PASS' if families >= 10 else 'FAIL'} ({families})")
    print(f"  Max fam >= 50K: {'PASS' if mc >= 50000 else 'FAIL'} ({mc})")
    print(f"  Total >= 100K: {'PASS' if total_members >= 100000 else 'FAIL'} ({total_members})")
    print(f"  All have relations: {'PASS' if members_without_relations == 0 else 'FAIL'} ({members_without_relations})")
