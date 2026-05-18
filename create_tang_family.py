"""Create Tang Dynasty Li Imperial Family genealogy."""
import sys
import os
from datetime import date
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User, Family, Member, FamilyRelation, Marriage
import bcrypt

def d(s):
    """Parse YYYY-MM-DD string to date, return None if empty."""
    if not s:
        return None
    parts = s.split('-')
    return date(int(parts[0]), int(parts[1]), int(parts[2]))

app = create_app()

with app.app_context():
    db.create_all()

    # Create account
    username = 'tang_li'
    password = 'tang123456'
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user = User.query.filter_by(username=username).first()
    if user:
        print(f'User "{username}" already exists, deleting old data...')
        for f in Family.query.filter_by(user_id=user.user_id).all():
            Member.query.filter_by(family_id=f.family_id).delete()
            db.session.delete(f)
        db.session.delete(user)
        db.session.commit()
        user = None

    if not user:
        user = User(username=username, password_hash=pw_hash, email='tang@dynasty.cn')
        db.session.add(user)
        db.session.commit()
        print(f'Created user: {username} / {password}')

    # Create family
    family = Family(user_id=user.user_id, family_name='李唐皇族',
                    description='唐朝皇室李氏家族谱系。唐朝（618年—907年），李渊建立，共历21帝，享国289年。')
    db.session.add(family)
    db.session.commit()
    print(f'Created family: {family.family_name} (id={family.family_id})')

    fid = family.family_id

    def add_member(name, gender, birth, death, gen, bio=''):
        m = Member(family_id=fid, name=name, gender=gender, birth_date=d(birth),
                   death_date=d(death), generation=gen, biography=bio, created_by=user.user_id)
        db.session.add(m)
        db.session.commit()
        return m

    def add_parent_child(parent, child, rel_type='biological'):
        if not FamilyRelation.query.filter_by(parent_id=parent.member_id, child_id=child.member_id).first():
            r = FamilyRelation(parent_id=parent.member_id, child_id=child.member_id, relation_type=rel_type)
            db.session.add(r)
            db.session.commit()

    def add_marriage(husband, wife, mdate=None):
        if not Marriage.query.filter_by(husband_id=husband.member_id, wife_id=wife.member_id).first():
            m = Marriage(husband_id=husband.member_id, wife_id=wife.member_id, marriage_date=d(mdate))
            db.session.add(m)
            db.session.commit()

    print('Creating Tang Dynasty members...')

    # === Generation 0: Ancestors ===
    li_hu = add_member('李虎', 'M', '0506-01-01', '0551-01-01', 0, '西魏八柱国之一，唐太祖。追尊景皇帝。')
    li_bing = add_member('李昞', 'M', '0536-01-01', '0572-01-01', 1, '北周唐国公。追尊元皇帝。')
    add_parent_child(li_hu, li_bing)

    du_shi = add_member('独孤氏', 'F', '0540-01-01', '0580-01-01', 1, '元贞皇后。独孤信之女。')
    add_marriage(li_bing, du_shi, '0560-01-01')

    # === Generation 2: Li Yuan (Gaozu) ===
    li_yuan = add_member('李渊', 'M', '0566-04-07', '0635-06-25', 2,
                         '唐高祖。唐朝开国皇帝（618-626年在位）。617年起兵反隋，618年称帝，定都长安。')
    add_parent_child(li_bing, li_yuan)
    dou_shi = add_member('窦氏', 'F', '0569-01-01', '0613-01-01', 2, '太穆皇后。窦毅之女。')
    add_marriage(li_yuan, dou_shi, '0588-01-01')

    # === Generation 3: Li Shimin (Taizong) and siblings ===
    li_jiancheng = add_member('李建成', 'M', '0589-01-01', '0626-07-02', 3,
                              '隐太子。李渊长子。玄武门之变中被杀。')
    add_parent_child(li_yuan, li_jiancheng)

    li_shimin = add_member('李世民', 'M', '0598-01-28', '0649-07-10', 3,
                           '唐太宗。唐朝第二位皇帝（626-649年在位）。'
                           '玄武门之变后继位，开创贞观之治。被尊为"天可汗"。')
    add_parent_child(li_yuan, li_shimin)
    wu_zhangsun = add_member('长孙氏', 'F', '0601-01-01', '0636-11-28', 3,
                             '文德皇后。长孙无忌之妹。贤德睿智，辅佐太宗开创盛世。')
    add_marriage(li_shimin, wu_zhangsun, '0613-01-01')

    li_yuanji = add_member('李元吉', 'M', '0603-01-01', '0626-07-02', 3,
                           '齐王。李渊第四子。玄武门之变中被杀。')
    add_parent_child(li_yuan, li_yuanji)

    li_pingyang = add_member('平阳公主', 'F', '0598-01-01', '0623-01-01', 3,
                             '李渊之女。娘子军统帅，助父起兵，中国历史上唯一以军礼下葬的公主。')
    add_parent_child(li_yuan, li_pingyang)

    # === Generation 4: Li Zhi (Gaozong) and siblings ===
    li_chengqian = add_member('李承乾', 'M', '0619-01-01', '0645-01-01', 4, '太子，李世民长子。因谋反被废。')
    add_parent_child(li_shimin, li_chengqian)

    li_tai = add_member('李泰', 'M', '0620-01-01', '0652-01-01', 4, '魏王。博学多才，主编《括地志》。')
    add_parent_child(li_shimin, li_tai)

    li_zhi = add_member('李治', 'M', '0628-07-21', '0683-12-27', 4,
                        '唐高宗。唐朝第三位皇帝（649-683年在位）。'
                        '继承贞观遗风，开创永徽之治。后因风疾，政事多由武则天裁决。')
    add_parent_child(li_shimin, li_zhi)

    wu_zetian = add_member('武则天', 'F', '0624-02-17', '0705-12-16', 4,
                           '中国历史上唯一的女皇帝（690-705年在位）。'
                           '太宗才人、高宗皇后。690年称帝，改国号为周。'
                           '在位期间推行科举、发展经济，史称"贞观遗风"。')
    add_marriage(li_zhi, wu_zetian, '0651-01-01')

    # Other Taizong children
    li_ke = add_member('李恪', 'M', '0619-01-01', '0653-01-01', 4, '吴王。文武双全，因房遗爱谋反案被冤杀。')
    add_parent_child(li_shimin, li_ke)

    li_zhen = add_member('李贞', 'M', '0627-01-01', '0688-01-01', 4, '越王。反对武则天称帝，起兵失败自杀。')
    add_parent_child(li_shimin, li_zhen)

    # === Generation 5: Sons of Li Zhi + Wu Zetian ===
    li_hong = add_member('李弘', 'M', '0652-01-01', '0675-01-01', 5, '孝敬皇帝。李治第五子，早逝追封皇帝。')
    add_parent_child(li_zhi, li_hong)
    add_parent_child(wu_zetian, li_hong, 'biological')

    li_xian = add_member('李贤', 'M', '0655-01-01', '0684-05-13', 5, '章怀太子。著有《后汉书注》。被武则天逼令自杀。')
    add_parent_child(li_zhi, li_xian)
    add_parent_child(wu_zetian, li_xian, 'biological')

    li_xian_zhongzong = add_member('李显', 'M', '0656-11-26', '0710-07-03', 5,
                                   '唐中宗。唐朝第四位皇帝。683-684年首次在位，'
                                   '705-710年复辟。被韦后毒杀。')
    add_parent_child(li_zhi, li_xian_zhongzong)
    add_parent_child(wu_zetian, li_xian_zhongzong, 'biological')

    wei_shi = add_member('韦氏', 'F', '0664-01-01', '0710-07-21', 5, '韦皇后。中宗皇后，效仿武则天干政。与安乐公主合谋毒杀中宗。')
    add_marriage(li_xian_zhongzong, wei_shi, '0680-01-01')

    li_dan = add_member('李旦', 'M', '0662-06-22', '0716-07-13', 5,
                        '唐睿宗。唐朝第五位皇帝。684-690年首次在位，710-712年复辟。主动禅位于李隆基。')
    add_parent_child(li_zhi, li_dan)
    add_parent_child(wu_zetian, li_dan, 'biological')

    li_taiping = add_member('太平公主', 'F', '0665-01-01', '0713-08-02', 5,
                            '武则天幼女。权倾朝野，后与李隆基争权失败被赐死。')
    add_parent_child(li_zhi, li_taiping)
    add_parent_child(wu_zetian, li_taiping, 'biological')

    # === Generation 6: Li Longji (Xuanzong) and siblings ===
    li_longji = add_member('李隆基', 'M', '0685-09-08', '0762-05-03', 6,
                           '唐玄宗（唐明皇）。唐朝第六位皇帝（712-756年在位）。'
                           '开创开元盛世，后因安史之乱被迫退位。'
                           '在位44年，为唐朝在位最长的皇帝。')
    add_parent_child(li_dan, li_longji)

    yang_guifei = add_member('杨玉环', 'F', '0719-06-22', '0756-07-15', 6,
                             '杨贵妃。中国古代四大美女之一。"羞花"之貌。'
                             '原为寿王妃，后入宫为玄宗贵妃。安史之乱中在马嵬坡被赐死。')
    add_marriage(li_longji, yang_guifei, '0745-01-01')

    wu_huifei = add_member('武惠妃', 'F', '0699-01-01', '0737-01-01', 6,
                           '玄宗前期宠妃。武则天侄孙女。')
    add_marriage(li_longji, wu_huifei, '0714-01-01')

    # Zhongzong's important child
    li_chongrun = add_member('李重润', 'M', '0682-01-01', '0701-01-01', 6, '懿德太子。中宗长子。因议论武则天私生活被杖杀。')
    add_parent_child(li_xian_zhongzong, li_chongrun)

    anle_princess = add_member('安乐公主', 'F', '0684-01-01', '0710-07-21', 6,
                               '中宗幼女。骄纵跋扈，与母韦后合谋毒杀中宗，后被李隆基所杀。')
    add_parent_child(li_xian_zhongzong, anle_princess)

    # === Generation 7: Xuanzong's sons ===
    li_mao = add_member('李瑁', 'M', '0720-01-01', '0775-01-01', 7,
                         '寿王。武惠妃之子。原配杨玉环被玄宗夺走。')
    add_parent_child(li_longji, li_mao)
    add_parent_child(wu_huifei, li_mao, 'biological')

    li_heng = add_member('李亨', 'M', '0711-02-21', '0762-05-16', 7,
                         '唐肃宗。唐朝第七位皇帝（756-762年在位）。'
                         '在马嵬坡与玄宗分道，于灵武即位，领导平定安史之乱。')
    add_parent_child(li_longji, li_heng)

    li_ying = add_member('李瑛', 'M', '0706-01-01', '0737-01-01', 7,
                         '太子。被武惠妃诬陷谋反，废为庶人并赐死。')
    add_parent_child(li_longji, li_ying)

    # === Generation 8: Suzong's son ===
    li_yu_daizong = add_member('李豫', 'M', '0727-01-09', '0779-06-10', 8,
                               '唐代宗。唐朝第八位皇帝（762-779年在位）。平定安史之乱，结束战乱。')
    add_parent_child(li_heng, li_yu_daizong)

    li_chuo = add_member('李倓', 'M', '0729-01-01', '0757-01-01', 8,
                         '建宁王。英勇善战，被张良娣诬陷赐死。后代宗追谥"承天皇帝"。')
    add_parent_child(li_heng, li_chuo)

    # === Generation 9: Dezong ===
    li_kuo = add_member('李适', 'M', '0742-05-27', '0805-02-25', 9,
                        '唐德宗。唐朝第九位皇帝（779-805年在位）。'
                        '在位前期励精图治，后期猜忌大臣，姑息藩镇。')
    add_parent_child(li_yu_daizong, li_kuo)

    # === Generation 10: Shunzong ===
    li_song = add_member('李诵', 'M', '0761-02-01', '0806-02-11', 10,
                         '唐顺宗。唐朝第十位皇帝（805年在位）。在位仅8个月。支持永贞革新。')
    add_parent_child(li_kuo, li_song)

    # === Generation 11: Xianzong ===
    li_chun = add_member('李纯', 'M', '0778-03-01', '0820-02-14', 11,
                         '唐宪宗。唐朝第十一位皇帝（805-820年在位）。开创"元和中兴"，平定藩镇。')
    add_parent_child(li_song, li_chun)

    # === Generations 12-13: Muzong → Jingzong/Wenzong/Wuzong ===
    li_heng_muzong = add_member('李恒', 'M', '0795-07-01', '0824-02-25', 12,
                                '唐穆宗。在位期间沉迷享乐，藩镇再度叛乱。')
    add_parent_child(li_chun, li_heng_muzong)

    li_zhan = add_member('李昂', 'M', '0809-11-20', '0840-02-10', 13,
                         '唐文宗。唐朝第十四位皇帝（827-840年在位）。'
                         '励精图治，发动"甘露之变"失败，被软禁抑郁而终。')
    add_parent_child(li_heng_muzong, li_zhan)

    li_yan = add_member('李炎', 'M', '0814-07-01', '0846-04-22', 13,
                        '唐武宗。唐朝第十五位皇帝（840-846年在位）。'
                        '灭佛运动（会昌法难），击败回鹘，平定泽潞。')
    add_parent_child(li_heng_muzong, li_yan)

    # === Xuanzong (not Li Longji, the later Xuanzong) ===
    li_chen = add_member('李忱', 'M', '0810-07-27', '0859-09-10', 12,
                         '唐宣宗。唐朝第十六位皇帝（846-859年在位）。'
                         '被称为"小太宗"，开创"大中之治"，为唐朝最后的辉煌时期。')
    add_parent_child(li_chun, li_chen)

    # === Late Tang representatives (skipping to last emperor) ===
    li_zhu = add_member('李柷', 'M', '0892-10-01', '0908-03-26', 17,
                        '唐哀帝。唐朝末代皇帝（904-907年在位）。被朱温逼迫禅让，唐朝灭亡。次年被毒杀。')
    # Li Zhu descends from Zhaozong, but for simplicity we just note him

    # === Famous cultural figures ===
    li_bai = add_member('李白', 'M', '0701-02-28', '0762-11-01', 6,
                        '诗仙。唐代伟大的浪漫主义诗人。与杜甫合称"李杜"。'
                        '据传为李唐宗室远支（凉武昭王李暠后裔）。')
    # Li Bai is a distant relative, connected via Li Gao line — we mark him as standalone

    # === Stats ===
    total_members = Member.query.filter_by(family_id=fid).count()
    total_relations = FamilyRelation.query.join(Member, FamilyRelation.parent_id == Member.member_id).filter(Member.family_id == fid).count()
    total_marriages = Marriage.query.join(Member, Marriage.husband_id == Member.member_id).filter(Member.family_id == fid).count()

    print(f'\nDone! Created:')
    print(f'  Members: {total_members}')
    print(f'  Parent-child relations: {total_relations}')
    print(f'  Marriages: {total_marriages}')
    print(f'\nLogin credentials:')
    print(f'  Username: {username}')
    print(f'  Password: {password}')
    print(f'\nAccess at: http://localhost:5000')
