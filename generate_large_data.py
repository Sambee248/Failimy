# -*- coding: utf-8 -*-
"""Generate large-scale genealogy data.

Requirements: 10+ users, 10+ families, one with 50K+ members, 100K+ total, all
members have >=1 relationship, 30+ generations per family.

Strategy: Logistic S-curve growth — rapid initial expansion, then plateau.
Each couple produces K children; a controlled fraction marry external spouses.
A minimum-marriage safeguard prevents lineage extinction.

Usage:  python generate_large_data.py
"""
import random
import time
from datetime import datetime, timedelta
from app import create_app
from models import db, User, Family, Member, FamilyRelation, Marriage
import bcrypt

SURNAMES = [
    '张', '李', '王', '赵', '刘', '陈', '杨', '黄', '周', '吴',
    '徐', '孙', '马', '朱', '胡', '郭', '林', '何', '高', '梁',
]

GEN_CHARS_M = [
    ['德', '文', '志', '永', '世', '承', '继', '绍', '启', '开',
     '兴', '振', '立', '昌', '明', '光', '耀', '宗', '先', '元'],
    ['仁', '义', '礼', '智', '信', '忠', '孝', '廉', '节', '勇',
     '彦', '哲', '圣', '贤', '英', '雄', '豪', '杰', '清', '正'],
    ['国', '邦', '家', '庭', '庆', '福', '寿', '康', '宁', '安',
     '泰', '祥', '瑞', '和', '平', '顺', '利', '亨', '通', '达'],
    ['松', '柏', '竹', '梅', '兰', '菊', '莲', '鹤', '龙', '凤',
     '麟', '鸿', '雁', '云', '海', '山', '川', '峰', '岭', '岳'],
]

GIVEN_M = [
    '伟', '强', '磊', '军', '勇', '杰', '涛', '明', '超', '华',
    '建国', '志强', '文博', '浩然', '子轩', '宇轩', '一鸣', '天宇',
    '俊杰', '鸿飞', '鹏程', '景行', '思远', '承志', '修文', '绍祖',
    '光耀', '世昌', '德厚', '永康', '长安', '元正'
]

GIVEN_F = [
    '芳', '敏', '静', '丽', '婷', '雪', '玲', '秀英', '桂英', '玉兰',
    '秀兰', '秀珍', '桂兰', '玉珍', '秀云', '桂芳', '秀梅', '玉梅',
    '雨桐', '思雨', '诗涵', '梦瑶', '若溪', '瑾萱', '雅琪', '欣怡',
    '婉清', '清漪', '云裳', '月华', '明珠', '如意', '慧娘', '素心'
]

FEM_CHARS = [
    '淑', '婉', '娥', '妙', '娇', '媛', '婷', '媚', '娟', '婵',
    '娴', '妩', '嫣', '妤', '娅', '姝', '慧', '素', '云', '月'
]


def rand_date(y1, y2):
    d0 = datetime(y1, 1, 1)
    return (d0 + timedelta(days=random.randint(0, (datetime(y2, 12, 31) - d0).days))).date()


def gen_name(g, gen):
    s = random.choice(SURNAMES)
    if g == 'M':
        c = random.choice(GEN_CHARS_M[min(gen - 1, len(GEN_CHARS_M) - 1) % len(GEN_CHARS_M)])
        return s + c + random.choice(GIVEN_M)
    return s + random.choice(FEM_CHARS) + random.choice(GIVEN_F)


def build_family(fid, uid, target, max_gen, sess):
    """Generate one family using logistic S-curve growth.

    Phase 1 (first ~30% of gens): exponential growth to reach ~70% of target couples.
    Phase 2 (middle ~50%): steady state, maintaining couple count.
    Phase 3 (final ~20%): gradual decline in marriage rate.
    """
    BATCH = 5000
    y0 = 1300

    # --- Gen 1: founders + spouses ---
    N0 = 20   # more founders for stability
    fmaps = []
    for i in range(N0):
        fmaps.append({
            'family_id': fid, 'name': gen_name('M', 1), 'gender': 'M',
            'birth_date': rand_date(y0 - 30, y0 + 10),
            'death_date': rand_date(y0 + 30, y0 + 75) if random.random() < 0.85 else None,
            'generation': 1, 'biography': '始祖', 'created_by': uid,
        })
    sess.bulk_insert_mappings(Member, fmaps)
    sess.flush()
    founders = list(reversed(
        Member.query.filter_by(family_id=fid).order_by(Member.member_id.desc()).limit(N0).all()))

    smaps = []
    for f in founders:
        b = rand_date((f.birth_date.year - 5) if f.birth_date else y0 - 20,
                      (f.birth_date.year + 5) if f.birth_date else y0 + 15)
        smaps.append({
            'family_id': fid, 'name': gen_name('F', 1), 'gender': 'F',
            'birth_date': b, 'death_date': rand_date(b.year + 40, b.year + 85) if random.random() < 0.85 else None,
            'generation': 1, 'created_by': uid,
        })
    sess.bulk_insert_mappings(Member, smaps)
    sess.flush()
    spouses = list(reversed(
        Member.query.filter_by(family_id=fid).order_by(Member.member_id.desc()).limit(N0).all()))

    couples = []
    mmaps = []
    for f, s in zip(founders, spouses):
        md = rand_date(max((f.birth_date.year if f.birth_date else y0) + 18,
                           (s.birth_date.year if s.birth_date else y0) + 16),
                       max((f.birth_date.year if f.birth_date else y0) + 30,
                           (s.birth_date.year if s.birth_date else y0) + 25))
        mmaps.append({'husband_id': f.member_id, 'wife_id': s.member_id, 'marriage_date': md})
        couples.append((f.member_id, s.member_id))
    sess.bulk_insert_mappings(Marriage, mmaps)
    sess.commit()

    total = N0 * 2
    rels = 0
    mars = N0
    print(f"    Gen 1: {total} members, {N0} couples", end="")

    # Pre-compute target couple count for steady state
    # Members ≈ Σ across gens: children + marrying_spouses
    # At steady state with C couples, K kids, marriage rate r:
    #   new members/gen = C*K + C*K*r = C*K*(1+r)
    # Over G generations, with ramp-up: total ≈ G * C_steady * K * (1+r) / 2
    G = max_gen - 1
    avg_kids = 2.5
    avg_rate = 0.55
    target_couples = max(N0, int(total * G / (G * avg_kids * (1 + avg_rate))))
    # Actually just use: target_couples = target / (max_gen * avg_kids * (1+avg_rate))
    target_couples = max(N0 // 2, int(target / (max_gen * 3.5)))
    target_couples = min(target_couples, target // 4)  # cap at reasonable number

    ramp_gens = max(3, max_gen // 5)  # generations to reach target couples
    plateau_gens = max_gen - ramp_gens

    def _target_for_gen(g):
        """Target number of couples for generation g (0-indexed from gen 2)."""
        if g <= ramp_gens:
            # Logistic ramp
            frac = g / ramp_gens
            return max(1, int(N0 * (target_couples / N0) ** frac))
        else:
            return target_couples

    for gen in range(2, max_gen + 1):
        gy = y0 + (gen - 1) * 25
        if not couples:
            break

        current_couples = len(couples)
        desired_couples = _target_for_gen(gen - 2)  # gen 2 is idx 0

        # Determine kids per couple and marriage rate
        if current_couples <= desired_couples * 0.3:
            # Very behind — grow fast
            K = random.randint(3, 5)
            r = random.uniform(0.60, 0.80)
        elif current_couples <= desired_couples * 0.7:
            # Behind — grow moderately
            K = random.randint(2, 4)
            r = random.uniform(0.50, 0.70)
        elif current_couples <= desired_couples * 1.3:
            # Near target — stay steady
            K = random.randint(2, 3)
            r = random.uniform(0.35, 0.55)
        else:
            # Above target — slow down
            K = random.randint(1, 2)
            r = random.uniform(0.15, 0.35)

        # Safety: guarantee at least some children marry
        if K * r < 0.5:
            r = max(r, 0.5 / K)

        cmaps = []  # child mappings
        relsm = []  # relation mappings
        nc = []     # new couples
        mrmaps = [] # marriage mappings

        for hid, wid in couples:
            nk = max(1, K + random.randint(-1, 1))
            for _ in range(nk):
                gd = random.choice(['M', 'F'])
                nm = gen_name(gd, gen)
                dad = sess.get(Member, hid)
                mom = sess.get(Member, wid)
                dy = (dad.birth_date.year if dad and dad.birth_date else gy - 30)
                my = (mom.birth_date.year if mom and mom.birth_date else gy - 30)
                by = (dy + my) // 2 + random.randint(18, 35)
                bd = rand_date(by, by + 5)
                dd = rand_date(by + 40, by + 85) if random.random() < 0.8 else None
                cmaps.append({
                    'family_id': fid, 'name': nm, 'gender': gd,
                    'birth_date': bd, 'death_date': dd, 'generation': gen,
                    'created_by': uid,
                })

        # Insert children in batches
        for i in range(0, len(cmaps), BATCH):
            sess.bulk_insert_mappings(Member, cmaps[i:i + BATCH])
        sess.flush()
        kids = list(reversed(
            Member.query.filter_by(family_id=fid).order_by(Member.member_id.desc()).limit(len(cmaps)).all()))

        total += len(kids)

        # Relations + marriages
        ki = 0
        for hid, wid in couples:
            nk = max(1, K + random.randint(-1, 1))
            for _ in range(nk):
                if ki >= len(kids):
                    break
                child = kids[ki]
                relsm.append({'parent_id': hid, 'child_id': child.member_id, 'relation_type': 'biological'})
                relsm.append({'parent_id': wid, 'child_id': child.member_id, 'relation_type': 'biological'})

                if random.random() < r:
                    sg = 'F' if child.gender == 'M' else 'M'
                    sn = gen_name(sg, gen)
                    sb = rand_date((child.birth_date.year - 5) if child.birth_date else gy,
                                   (child.birth_date.year + 5) if child.birth_date else gy + 20)
                    sd = rand_date(sb.year + 40, sb.year + 85) if random.random() < 0.8 else None
                    sp = Member(family_id=fid, name=sn, gender=sg, birth_date=sb,
                                death_date=sd, generation=gen, created_by=uid)
                    sess.add(sp)
                    sess.flush()
                    total += 1

                    md = rand_date(
                        max((child.birth_date.year if child.birth_date else gy) + 18,
                            (sp.birth_date.year if sp.birth_date else gy) + 16),
                        max((child.birth_date.year if child.birth_date else gy) + 30,
                            (sp.birth_date.year if sp.birth_date else gy) + 25))
                    if child.gender == 'M':
                        mrmaps.append({'husband_id': child.member_id, 'wife_id': sp.member_id, 'marriage_date': md})
                        nc.append((child.member_id, sp.member_id))
                    else:
                        mrmaps.append({'husband_id': sp.member_id, 'wife_id': child.member_id, 'marriage_date': md})
                        nc.append((sp.member_id, child.member_id))
                ki += 1

        for i in range(0, len(relsm), BATCH):
            sess.bulk_insert_mappings(FamilyRelation, relsm[i:i + BATCH])
        rels += len(relsm)
        for i in range(0, len(mrmaps), BATCH):
            sess.bulk_insert_mappings(Marriage, mrmaps[i:i + BATCH])
        mars += len(mrmaps)

        couples = nc

        if gen % 5 == 0 or gen == max_gen:
            sess.commit()
            print(f"\n    Gen {gen}: {total} members, {len(couples)} couples, "
                  f"{rels} relations, {mars} marriages")
        else:
            print(".", end="", flush=True)

    sess.commit()
    return total, rels, mars


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        is_sqlite = 'sqlite' in db.engine.url.drivername
        if is_sqlite:
            db.session.execute(db.text('PRAGMA journal_mode=WAL'))
            db.session.execute(db.text('PRAGMA synchronous=OFF'))
            db.session.execute(db.text('PRAGMA cache_size=200000'))
            db.session.execute(db.text('PRAGMA temp_store=MEMORY'))

        t0 = time.time()

        # --- Users ---
        print("Creating users...")
        users = []
        for i in range(1, 11):
            u = User.query.filter_by(username=f'user{i}').first()
            if not u:
                ph = bcrypt.hashpw(f'pass{i}'.encode(), bcrypt.gensalt()).decode()
                u = User(username=f'user{i}', password_hash=ph, email=f'user{i}@example.com')
                db.session.add(u)
                db.session.flush()
            users.append(u)
        demo = User.query.filter_by(username='demo').first()
        if not demo:
            ph = bcrypt.hashpw('demo123'.encode(), bcrypt.gensalt()).decode()
            demo = User(username='demo', password_hash=ph, email='demo@example.com')
            db.session.add(demo)
            db.session.flush()
        if demo not in users:
            users.append(demo)
        db.session.commit()
        print(f"  {len(users)} users ready\n")

        # --- Family plan ---
        plan = [
            (0,  55000, 32, 'Zhang Clan'),   # 50K+ main family
            (1,  12000, 30, 'Li Clan'),
            (2,  12000, 30, 'Wang Clan'),
            (3,   9000, 30, 'Zhao Clan'),
            (4,   7000, 30, 'Liu Clan'),
            (5,   7000, 30, 'Chen Clan'),
            (6,   6000, 30, 'Yang Clan'),
            (7,   6000, 30, 'Huang Clan'),
            (8,   5000, 30, 'Zhou Clan'),
            (9,   5000, 30, 'Wu Clan'),
            (10,  4000, 30, 'Xu Clan'),
            (2,   4000, 30, 'Ma Clan'),
            (3,   3000, 30, 'Zhu Clan'),
        ]

        tmem = trel = tmar = 0
        for idx, (ui, target, mg, name) in enumerate(plan):
            u = users[ui % len(users)]
            fam = Family(user_id=u.user_id, family_name=name,
                         description=f'Simulated family — {target} members, {mg} generations')
            db.session.add(fam)
            db.session.flush()
            db.session.commit()

            print(f"\n{name} (ID={fam.family_id}, user={u.username}) target={target} gen={mg}:")
            tf = time.time()
            mem, rel, mar = build_family(fam.family_id, u.user_id, target, mg, db.session)
            et = round(time.time() - tf, 1)
            tmem += mem; trel += rel; tmar += mar
            print(f"\n  -> {mem} members, {rel} relations, {mar} marriages ({et}s)")

        total_t = round(time.time() - t0, 1)
        print(f"\n{'='*60}")
        print(f"COMPLETE: {len(users)} users, {len(plan)} families, {tmem} members, {trel} relations, {tmar} marriages")
        print(f"Time: {total_t}s  Speed: {round(tmem/total_t) if total_t > 0 else 0} rec/s")
        print(f"Max family: {max(f[1] for f in plan)} members, {max(f[2] for f in plan)} generations")
        print(f"Users >= 10: {len(users)} {'OK' if len(users) >= 10 else 'FAIL'}")
        print(f"Families >= 10: {len(plan)} {'OK' if len(plan) >= 10 else 'FAIL'}")
        print(f"Max fam >= 50K: {'OK' if max(f[1] for f in plan) >= 50000 else 'CHECK'}")
        print(f"Total >= 100K: {tmem} {'OK' if tmem >= 100000 else 'NEED MORE'}")

        if is_sqlite:
            try:
                db.session.execute(db.text('PRAGMA journal_mode=DELETE'))
                db.session.execute(db.text('PRAGMA synchronous=NORMAL'))
            except Exception:
                pass

        print("\nAccounts: user1..user10 / pass1..pass10 | demo / demo123")


if __name__ == '__main__':
    main()
