"""Generate mock genealogy data for testing.

Usage:
    python generate_data.py                    # Generate 5 families with ~500 members each
    python generate_data.py --families 10 --members 5000  # 10 families, ~5000 each
    python generate_data.py --user-id 1 --families 2 --members 100  # Specific user
"""
import argparse
import random
import sys
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Family, Member, FamilyRelation, Marriage
import bcrypt

# Chinese surname pools
SURNAMES_MALE = [
    '张', '李', '王', '赵', '刘', '陈', '杨', '黄', '周', '吴',
    '徐', '孙', '马', '朱', '胡', '郭', '林', '何', '高', '梁',
    '郑', '罗', '宋', '谢', '唐', '韩', '曹', '许', '邓', '冯'
]
SURNAMES_FEMALE = [
    '李', '王', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '马', '朱', '胡', '郭', '林', '何', '高', '郑',
    '梁', '罗', '宋', '谢', '唐', '韩', '曹', '许', '邓', '冯'
]

GIVEN_NAMES_MALE = [
    '伟', '强', '磊', '军', '勇', '杰', '涛', '明', '超', '华',
    '建国', '志强', '文博', '浩然', '子轩', '宇轩', '一鸣', '天宇',
    '俊杰', '鸿飞', '鹏程', '景行', '思远', '承志', '修文', '绍祖',
    '光耀', '世昌', '德厚', '永康', '长安', '元正', '守仁', '继祖'
]

GIVEN_NAMES_FEMALE = [
    '芳', '敏', '静', '丽', '婷', '雪', '玲', '秀英', '桂英', '玉兰',
    '秀兰', '秀珍', '桂兰', '玉珍', '秀云', '桂芳', '秀梅', '玉梅',
    '雨桐', '思雨', '诗涵', '梦瑶', '若溪', '瑾萱', '雅琪', '欣怡',
    '婉清', '清漪', '云裳', '月华', '明珠', '如意', '慧娘', '素心'
]

GENERATION_NAMES_MALE = [
    ['祖', '宗', '先', '元', '太', '高', '曾', '承', '继', '绍',
     '启', '开', '兴', '振', '立', '永', '世', '昌', '明', '德'],
    ['仁', '义', '礼', '智', '信', '忠', '孝', '廉', '节', '勇',
     '文', '武', '彦', '哲', '圣', '贤', '英', '雄', '豪', '杰'],
    ['国', '邦', '家', '庭', '庆', '福', '寿', '康', '宁', '安',
     '泰', '祥', '瑞', '和', '平', '顺', '利', '亨', '通', '达'],
    ['松', '柏', '竹', '梅', '兰', '菊', '莲', '鹤', '龙', '凤',
     '麟', '龟', '虎', '豹', '鹰', '鹏', '鸿', '雁', '鹤', '鸾']
]

FEMALE_NAME_CHARS = ['淑', '婉', '娥', '妙', '娇', '媛', '婷', '媚', '娟', '婵',
                     '娴', '妩', '嫣', '妤', '姒', '妲', '妃', '姬', '姝', '娅']


def generate_name(gender, generation):
    surname = random.choice(SURNAMES_MALE if gender == 'M' else SURNAMES_FEMALE)
    if gender == 'M':
        gen_char = GENERATION_NAMES_MALE[min(generation - 1, len(GENERATION_NAMES_MALE) - 1) % len(GENERATION_NAMES_MALE)]
        given = random.choice(gen_char) + random.choice(GIVEN_NAMES_MALE)
    else:
        given = random.choice(FEMALE_NAME_CHARS) + random.choice(GIVEN_NAMES_FEMALE)
    return surname + given


def random_date(start_year, end_year):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).date()


def create_demo_user():
    """Create a demo user if not exists."""
    user = User.query.filter_by(username='demo').first()
    if not user:
        password_hash = bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(username='demo', password_hash=password_hash, email='demo@example.com')
        db.session.add(user)
        db.session.commit()
        print("Created demo user: username='demo', password='demo123'")
    return user


def generate_family(user, family_index):
    """Generate one complete family tree."""
    family_name = f"{random.choice(['张', '李', '王', '赵', '刘', '陈', '杨', '黄', '周', '吴'])}氏族谱"
    if family_index > 0:
        family_name = f"{random.choice(SURNAMES_MALE)}氏族谱"

    family = Family(
        user_id=user.user_id,
        family_name=family_name,
        description=f"第{family_index + 1}个测试家族，自动生成模拟数据"
    )
    db.session.add(family)
    db.session.flush()
    return family


def generate_generation(family, generation, parents_list, target_members, max_gen, all_members):
    """Generate one generation of members. Returns list of (husband, wife) couples for next generation."""
    year_base = 1500 + generation * 25
    couples = []

    if generation == 1:
        # Founder generation: create 2-4 founders
        num_founders = random.randint(2, 4)
        founders = []
        for _ in range(num_founders):
            gender = 'M'
            name = generate_name(gender, generation)
            birth = random_date(year_base - 20, year_base + 5)
            death = random_date(year_base + 40, year_base + 85) if random.random() < 0.9 else None
            member = Member(
                family_id=family.family_id,
                name=name, gender=gender, birth_date=birth,
                death_date=death, generation=generation,
                biography=f"{family.family_name}第{generation}代始祖"
            )
            db.session.add(member)
            db.session.flush()
            all_members.append(member)
            founders.append(member)

        # Pair founders
        for i in range(0, len(founders) - 1, 2):
            husband = founders[i]
            # Create wife for this founder
            wife_name = generate_name('F', generation)
            wife_birth = random_date(husband.birth_date.year - 5, husband.birth_date.year + 5) if husband.birth_date else random_date(year_base - 15, year_base + 10)
            wife_death = random_date(wife_birth.year + 40, wife_birth.year + 85) if random.random() < 0.9 else None
            wife = Member(
                family_id=family.family_id,
                name=wife_name, gender='F', birth_date=wife_birth,
                death_date=wife_death, generation=generation
            )
            db.session.add(wife)
            db.session.flush()
            all_members.append(wife)

            marriage = Marriage(husband_id=husband.member_id, wife_id=wife.member_id,
                               marriage_date=random_date(max(husband.birth_date.year if husband.birth_date else year_base,
                                                              wife.birth_date.year if wife.birth_date else year_base) + 18,
                                                         max(husband.birth_date.year if husband.birth_date else year_base,
                                                             wife.birth_date.year if wife.birth_date else year_base) + 25))
            db.session.add(marriage)
            db.session.flush()
            couples.append((husband, wife))

    else:
        # Generate children for each parent couple
        for husband, wife in parents_list:
            num_children = random.randint(2, 5)
            children = []
            for _ in range(num_children):
                gender = random.choice(['M', 'F'])
                name = generate_name(gender, generation)
                # Child born 18-35 years after parents' average birth year
                dad_year = husband.birth_date.year if husband.birth_date else year_base - 10
                mom_year = wife.birth_date.year if wife.birth_date else year_base - 10
                parent_avg_year = (dad_year + mom_year) // 2
                child_birth_year = parent_avg_year + random.randint(18, 35)
                birth = random_date(child_birth_year, child_birth_year + 5)
                death = random_date(child_birth_year + 40, child_birth_year + 85) if random.random() < 0.8 else None

                member = Member(
                    family_id=family.family_id,
                    name=name, gender=gender, birth_date=birth,
                    death_date=death, generation=generation
                )
                db.session.add(member)
                db.session.flush()
                all_members.append(member)
                children.append(member)

                # Create parent-child relations
                rel1 = FamilyRelation(parent_id=husband.member_id, child_id=member.member_id,
                                     relation_type='biological')
                rel2 = FamilyRelation(parent_id=wife.member_id, child_id=member.member_id,
                                     relation_type='biological')
                db.session.add(rel1)
                db.session.add(rel2)

            # Pair up children for next generation (only opposite-sex pairs)
            males = [c for c in children if c.gender == 'M']
            females = [c for c in children if c.gender == 'F']

            # Cross-pairing: each male gets a female spouse from the pool
            for male in males:
                spouse = None
                if females:
                    spouse = random.choice(females)
                    females.remove(spouse)
                else:
                    # Create a new female spouse from outside
                    spouse = Member(
                        family_id=family.family_id,
                        name=generate_name('F', generation),
                        gender='F',
                        birth_date=random_date(male.birth_date.year - 5, male.birth_date.year + 5) if male.birth_date else random_date(year_base, year_base + 20),
                        death_date=None,
                        generation=generation
                    )
                    db.session.add(spouse)
                    db.session.flush()
                    all_members.append(spouse)

                marriage_year = max(
                    (male.birth_date.year if male.birth_date else year_base) + 18,
                    (spouse.birth_date.year if spouse.birth_date else year_base) + 16
                )
                marriage_date = random_date(marriage_year, marriage_year + 10)
                marriage = Marriage(husband_id=male.member_id, wife_id=spouse.member_id,
                                   marriage_date=marriage_date)
                db.session.add(marriage)
                db.session.flush()
                couples.append((male, spouse))

            # Remaining females paired with outside males
            for female in females:
                husband = Member(
                    family_id=family.family_id,
                    name=generate_name('M', generation),
                    gender='M',
                    birth_date=random_date(female.birth_date.year - 5, female.birth_date.year + 5) if female.birth_date else random_date(year_base, year_base + 20),
                    death_date=None,
                    generation=generation
                )
                db.session.add(husband)
                db.session.flush()
                all_members.append(husband)

                marriage_year = max(
                    (husband.birth_date.year if husband.birth_date else year_base) + 18,
                    (female.birth_date.year if female.birth_date else year_base) + 16
                )
                marriage = Marriage(husband_id=husband.member_id, wife_id=female.member_id,
                                   marriage_date=random_date(marriage_year, marriage_year + 10))
                db.session.add(marriage)
                db.session.flush()
                couples.append((husband, female))

    return couples


def main():
    parser = argparse.ArgumentParser(description='Generate mock genealogy data')
    parser.add_argument('--families', type=int, default=5, help='Number of families (default: 5)')
    parser.add_argument('--members', type=int, default=5000, help='Target members per family (default: 5000)')
    parser.add_argument('--user-id', type=int, default=None, help='Existing user ID to assign families to')
    parser.add_argument('--create-user', action='store_true', default=True, help='Create demo user')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        db.create_all()

        if args.user_id:
            user = User.query.get(args.user_id)
            if not user:
                print(f"User {args.user_id} not found.")
                sys.exit(1)
        else:
            user = create_demo_user()

        print(f"Generating {args.families} families for user '{user.username}' (ID: {user.user_id})...")
        total_members = 0

        for fi in range(args.families):
            family = generate_family(user, fi)
            all_members = []
            couples = []

            # Calculate generations needed: roughly sqrt of members (2-4 children per couple)
            # For 5000 members, need about 15-16 generations
            max_generations = 1
            estimated = 0
            while estimated < args.members:
                max_generations += 1
                couples_count = 2 ** (max_generations - 2)  # rough estimate
                estimated = couples_count * 3 * (max_generations)

            max_generations = min(max_generations, 20)
            print(f"  Family '{family.family_name}': generating ~{max_generations} generations...")

            for gen in range(1, max_generations + 1):
                couples = generate_generation(family, gen, couples, args.members, max_generations, all_members)
                if gen % 5 == 0:
                    db.session.commit()
                    print(f"    Generation {gen}: {len(all_members)} members so far, {len(couples)} couples")

            db.session.commit()
            total_members += len(all_members)
            print(f"  Family '{family.family_name}' done: {len(all_members)} members, "
                  f"{FamilyRelation.query.join(Member, FamilyRelation.parent_id == Member.member_id).filter(Member.family_id == family.family_id).count()} relations, "
                  f"{Marriage.query.join(Member, (Marriage.husband_id == Member.member_id) | (Marriage.wife_id == Member.member_id)).filter(Member.family_id == family.family_id).distinct().count()} marriages")

        print(f"\nDone! Generated {total_members} total members across {args.families} families.")
        print(f"Login with: username='demo', password='demo123'")


if __name__ == '__main__':
    main()
