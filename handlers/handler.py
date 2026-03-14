from sqlalchemy.orm import Session
from sqlalchemy import select
from telebot import types

from db.models import PayMetadata, User


def ref_handler(session: Session, user: User, pay_metadata: PayMetadata):
    user_ref = get_user_ref(session, user)
    admin_user = session.execute(select(User).where(User.id == 1)).scalar()
    total_pay_moneys = pay_metadata.price * (pay_metadata.procent_balance / 100)
    total_inner_pay_moneys = pay_metadata.price * (pay_metadata.inner_balance / 100)
    for i in range(1, 13):
        need_level = need_ref_level(i)
        pay_moneys = total_pay_moneys * get_ref_procent(i) / 100
        inner_pay_moneys = total_inner_pay_moneys * get_ref_inner_procent(i) / 100
        print(pay_moneys)
        if user_ref.ref_level >= need_level: 
            user_ref.balance += pay_moneys # начисление денег
            user_ref.inner_balance += inner_pay_moneys # начисление денег
        else:
            admin_user.inner_balance += inner_pay_moneys # начисление денег
            admin_user.balance += pay_moneys
        print(i, user_ref.id)  
        user_ref = get_user_ref(session, user_ref)              
    session.commit()

def get_user_ref(session: Session, user: User):
    if user.ref == 1:
        return session.execute(select(User).where(User.id == user.ref)).scalar()
    return session.execute(select(User).where(User.tg_id == user.ref)).scalar()
def get_list_refs(session: Session, users: list):
    l = []
    for user in users:
        l.extend(session.execute(select(User).where(User.ref == user.tg_id, User.ref != 1)).scalars().all())
    return l
def need_ref_level(line: int):
    if line == 1: return 1
    if line == 2 or line == 3: return 2
    if line == 4 or line == 5: return 3
    if line == 6 or line == 7: return 4
    if line == 8 or line == 9: return 5
    if line > 9: return 6

def get_ref_procent(line: int):
    if line == 1: return 40
    if line == 2: return 20
    if line == 3: return 14
    if line == 4: return 6
    if line == 5: return 6
    if line == 6: return 4
    if line == 7: return 4
    if line == 8: return 3
    if line == 9: return 2
    if line == 10: return 0.5
    if line == 11: return 0.25
    if line == 12: return 0.125
    
def get_ref_inner_procent(line: int):
    if line == 1: return 40
    if line == 2: return 40
    if line == 3: return 20
    else: return 0