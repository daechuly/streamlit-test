######################################################################################################################
## 2024.09.06 Daechul YANG
######################################################################################################################
# from ast import Not
# from matplotlib import container
import streamlit as st
import pymysql
import pandas as pd
import datetime
import bcrypt    # password 암호화
import base64    #  passwordd 암호화
import json
from datetime import date

# import cryptography

############################# DB접속경로
with open('edge_config.json', 'r', encoding='utf-8') as f:
    db_config = json.load(f)


############################ column 이름 및 포맷 변경
col_config={'TRAIN_DT': st.column_config.DateColumn('강습일자', format="MM-DD ddd"),
            'TRAINER': '코치명',
            'TRAINEE': '회원이름',
            'UPDATE_DT': st.column_config.DateColumn('수정일시', format="MM-DD HH:mm"),
            'CONFIRM_FLAG': '신청상태'
}

cols = ['TRAIN_DT', 'TRAINER', 'TRAINEE', 'UPDATE_DT', 'CONFIRM_FLAG']


## DB 접속 ######################################################################

def create_db_connection():
    db_conn = pymysql.connect(**db_config)
    return db_conn


## 강습신청 현황 조회 ######################################################################

def read_train(sd:date, ed:date):
    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "SELECT * FROM train_plan where date(train_dt) between date(%s) and date(%s) order by confirm_flag, train_dt, trainer, update_dt"
    
    try:
        curs.execute(sql, (sd, ed))
        result = curs.fetchall()
    
    except Exception as ex:
        st.error(str(ex))
        st.stop()

    finally:
        curs.close()
        db_conn.close()
    
    if not result:
        return pd.DataFrame()

    colus = [desc[0] for desc in curs.description]     ## 컬럼 이름 가져오기
    df = pd.DataFrame(result, columns=colus)
    
    df.index += 1

    return df


## 강습일정 입력 ###################################################

def insert_train(trainee: str, train_dt: date, trainer: str):

    rr = check_insert_train(trainee, train_dt)
    if rr:
        st.error(f"해당 주차에 이미 신청되었습니다. {rr.strftime('%Y-%m-%d')}")
        st.stop()
        return 

    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "INSERT INTO train_plan (TRAINEE, TRAIN_DT, TRAINER) VALUES (%s, %s, %s)"
    val = (trainee, train_dt, trainer)

    try:
        curs.execute(sql, val)
        db_conn.commit()
        
    except Exception as ex:
        db_conn.rollback()
        if '1062' in str(ex):
            st.error(f"이미 신청되었습니다. {trainee} {train_dt.strftime('%Y-%m-%d %a')} (취소 후 재신청 불가)")
        elif '1452' in str(ex):
            st.error(f"먼저 회원 등록바랍니다.  {trainee}")
        else:
            st.error(str(ex))
        st.stop()
      
    finally:
        curs.close()
        db_conn.close()


## 동일 주차 기 신청여부 확인 ###################################################???????????????????????????????????????

def check_insert_train(trainee: str, train_dt: date):

    w = train_dt.strftime('%w')
    sd = train_dt - datetime.timedelta(days=int(w))
    ed = train_dt + datetime.timedelta(days=(6-int(w)))

    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "SELECT train_dt FROM train_plan where trainee = %s and CONFIRM_FLAG <> '취소' and date(train_dt) between date(%s) and date(%s)"
    
    try:
        curs.execute(sql, (trainee, sd, ed))
        result = curs.fetchall()
    
    except Exception as ex:
        st.error(str(ex))
        st.stop()

    finally:
        curs.close()
        db_conn.close()

    if not result:
        return False
    else:
        return result[0][0]

    

## 요청일자 이후로 금주/차주 강습 가능한 일정 선택  ###################################################

def train_day_list(tr_date: date):
    yw = None    ## 두주에 걸쳐 강습일정 표시되지 않도록 주차 저장
    ll = []

    for ii in range(7):
        if tr_date.strftime('%a') in(['Tue','Thu']):     ## 화/목요일만 강습일정 추가      
            ll.append(tr_date.strftime('%Y/%m/%d %a'))
            yw = tr_date.strftime('%Y%W')

        tr_date += datetime.timedelta(days=1)
        if (yw != None) & (yw != tr_date.strftime('%Y%W')):    ## 해당 주차만 신청 가능 
            break

    return ll

     
## 이미 신청한 강습 취소 ###################################################

def cancel_train(df: pd.DataFrame):
    db_conn = create_db_connection()
    curs = db_conn.cursor()
    cnt = 0
    for ii in range(len(df)):
        sql = "UPDATE train_plan Set CONFIRM_FLAG = '취소', UPDATE_DT = CURRENT_TIMESTAMP \
            where train_dt = %s and TRAINEE = %s and confirm_flag = '신청'"   
            
        val = (df.iloc[ii].TRAIN_DT, df.iloc[ii].TRAINEE)    
                
        try:    
            curs.execute(sql, val)
            db_conn.commit()
            cnt += curs.rowcount
            
        except Exception as ex:
            db_conn.rollback()
            st.error(str(ex))
            st.stop()
                            
    curs.close()
    db_conn.close()
    
    st.success(str(cnt)+'명 취소되었습니다.')


## 신청한 강습 요청에 대해 일정 확정 ###################################################
    
def confirm_train(df: pd.DataFrame, work_gbn: str):
    db_conn = create_db_connection()
    curs = db_conn.cursor()
    
    cnt=0
  
    for ii in range(len(df)):
        sql = "UPDATE train_plan Set CONFIRM_FLAG = %s where train_dt = %s and TRAINEE = %s"
        val = (work_gbn, df.iloc[ii].TRAIN_DT, df.iloc[ii].TRAINEE)    
                
        try:    
            curs.execute(sql, val)
            cnt += curs.rowcount
            db_conn.commit()

        except Exception as ex:
            db_conn.rollback()
            curs.close()
            db_conn.close()
            st.error(str(ex))
            return False

    curs.close()
    db_conn.close()
    st.success(str(cnt)+' 명 '+ work_gbn + ' 처리 되었습니다')
    return True
    

## dataframe selected ###################################################

def dataframe_with_selections(df: pd.DataFrame):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        use_container_width=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True),
                       'TRAIN_DT': st.column_config.DateColumn('강습일자', format="MM-DD ddd"),
                        'TRAINER': '코치명',
                        'TRAINEE': '회원이름',
                        'UPDATE_DT': st.column_config.DateColumn('수정일시', format="MM-DD HH:MM"),
                        'CONFIRM_FLAG': '신청상태'},
        disabled=df.columns,
    )
    # Filter the dataframe using the temporary column
    selected_rows = edited_df[edited_df["Select"]]
    
    return selected_rows.drop("Select", axis=1)


## 강사 조회 #################################################################

def read_trainer():
    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "SELECT * FROM trainers order by trainer;"
    
    try:
        curs.execute(sql)
        
        if curs.rowcount < 1:
            st.error('등록된 코치가 없습니다')
            return None
        else:
            result = curs.fetchall()
    
    except Exception as ex:
        st.error(str(ex))
        return None
    
    finally:
        curs.close()
        db_conn.close()

    return [rr[0] for rr in result]


## 첫 화면 로그인 처리 #################################################################

def login_session(in_name: str, in_pwd: str):
    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = 'set sql_safe_updates=0;'    ## DB 최초 접속 후 수정 가능한 모드로 전환
    curs.execute(sql)

    sql = "SELECT trainee, passwd, admin_flag FROM trainees where trainee = %s"
        
    try:
        curs.execute(sql, (in_name))
        
        if curs.rowcount < 1:
            st.warning('등록되지 않은 회원입니다.')
            return False
        else:
            result = curs.fetchone()
    
    except Exception as ex:
        st.error(str(ex))
        return False

    finally:
        curs.close()
        db_conn.close()
        
    hashed = base64.b64decode(result[1].encode('utf-8'))     ## 비밀번호 비교 확인
    if not bcrypt.checkpw(in_pwd.encode(), hashed):
        st.warning('비밀번호 오류 입니다.')
        return False

    st.session_state.trainee = result[0]
    st.session_state.admin_flag = result[2]

    st.success('로그인 되었습니다.')
    return True

## 회원 등록 #################################################################

def insert_trainee(in_name: str, in_pwd: str):
    if len(in_pwd) < 4:
        st.error('비밀번호는 4자 이상 입력하세요.')
        return False

    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "INSERT INTO trainees (TRAINEE, passwd) VALUES (%s, %s)"
    
    hashed = bcrypt.hashpw(in_pwd.encode(), bcrypt.gensalt())
    hashed = base64.b64encode(hashed).decode('utf-8')
    val = (in_name, hashed)

    try:
        curs.execute(sql, val)
            
    except Exception as ex:
        db_conn.rollback()
        if '1062' in str(ex):
            st.error(f"이미 등록된 회원입니다.  {in_name}")
        else:
            st.error(str(ex))
            
        return False
    
    else:
        db_conn.commit()
            
    finally:
        curs.close()
        db_conn.close()

    st.success('회원으로 가입되었습니다.' + in_name)
    return True
    
## 비밀 번호 변경 #################################################################

def change_passwd(in_name: str, in_pwd: str):
    db_conn = create_db_connection()
    curs = db_conn.cursor()

    hashed = bcrypt.hashpw(in_pwd.encode(), bcrypt.gensalt())
    hashed = base64.b64encode(hashed).decode('utf-8')

    sql = "UPDATE trainees Set passwd = %s where trainee = %s"
    val = (hashed, in_name)    
            
    try:    
        curs.execute(sql, val)
        
    except Exception as ex:
        db_conn.rollback()
        st.error(str(ex))
        return False
    
    else:
        if curs.rowcount < 1:
            st.warning('등록되지 않은 회원입니다. '+in_name )
            return False
        else:        
            db_conn.commit()

    finally:
        curs.close()
        db_conn.close()    
    
    st.success('비밀번호가 변경 되었습니다.'+in_name)
    return True

## 화면 접근을 위한 로그인 여부 확인 ####################################################### 

def check_access():
    if 'trainee' not in st.session_state:
        st.warning('로그인 후 사용바랍니다.')
        return False
    else:
        return True

## 관리자 화면 접근을 위한 권한 확인 ############################################################

def check_admin_access():
    if 'admin_flag' not in st.session_state:
        st.warning('로그인 후 사용바랍니다.')
        return False
    
    if not st.session_state.admin_flag:
        st.warning(f"관리자 화면입니다. -{st.session_state.trainee}-")
        return False
    
    return True


#################################################################################################
## Main Menu #################################################################################################

## 로그인 화면 HOME ############################################################

def main_home():
    
    st.text_input(label="이름을 입력하세요.", key='main_home_in_name')
    st.text_input(label='비밀번호를 입력하세요', type='password', key='main_home_in_pwd')

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(label='로그인', type='primary'):
            login_session(st.session_state.main_home_in_name, st.session_state.main_home_in_pwd)
    
    if 'trainee' not in st.session_state:
        with col2:
            if st.button(label='회원 가입'):
                insert_trainee(st.session_state.main_home_in_name, st.session_state.main_home_in_pwd)

    if 'trainee' in st.session_state:
        with col3:
            if st.button(label='비밀번호 변경'):
                change_passwd(st.session_state.trainee, st.session_state.main_home_in_pwd)
    

## 신청현황 조회 ############################################################

def main_query():
    
    if not check_access():
        return
    
    min_date = datetime.date.today() - datetime.timedelta(weeks=6)   ## 최소 6주 전 부터   
    max_date = datetime.date.today() + datetime.timedelta(weeks=1)   ## 최대 1주 후 까지

    rdo = st.radio(label="조회범위를 선택하세요", options=["하루", "기간"], horizontal=True)

    if rdo == '하루':
        start_date = st.date_input(label="조회 일자를 선택하세요.", min_value=min_date, max_value=max_date)
        end_date = start_date

    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(label="시작 일자를 선택하세요.", min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input(label="종료 일자를 선택하세요.", min_value=min_date, max_value=max_date)


    if st.button(label="조회", type='primary'):    
        df = read_train(start_date, end_date)
        if len(df) < 1:
            st.warning("조회범위에 데이터가 없습니다.")
            st.stop()
        
        st.dataframe(df[cols],  use_container_width=True, column_config=col_config)
        st.write(str(len(df))+'명 조회되었습니다.')


## 신규 강습 신청 (개인) ############################################################

def main_regist():

    if not check_access():
        return
    
    in_date=st.date_input(label="신청 기준일", disabled=True)   
    
    rdo_train_date = st.radio(label="강습 일자를 선택하세요.", options=train_day_list(in_date), horizontal=True) 
    tr_date = datetime.datetime.strptime(rdo_train_date[:10], '%Y/%m/%d')
    
    w = tr_date.strftime('%w')

    start_date, end_date = tr_date, tr_date     
  
    df = read_train(start_date, end_date)
    
    placeholder=st.empty()
    
    if len(df) > 0:
        placeholder.dataframe(df[cols], use_container_width=True, column_config=col_config)
        df = df[df['CONFIRM_FLAG'] == '신청']
        if len(df) == 0:
            st.warning('신청한 사람이 없습니다.')
    else:
        st.warning('신청한 사람이 없습니다.')

    in_name = st.text_input(label="강습받을 회원 이름을 입력하세요.", value=st.session_state.trainee, disabled=not st.session_state.admin_flag, key='main_regist_in_name')

    rdo_trainer = st.radio(label="강사를 선택하세요.", options=read_trainer(), horizontal=True) 

    if (tr_date.strftime('%w') == '4') & (rdo_trainer == '유남규(구)'):
        st.warning('목요일은 '+rdo_trainer+'코치님은 신청 불가합니다.')
        st.stop()

    in_trainer = rdo_trainer

    if st.button('저장', key='main_regist_btn', type='primary'):
        trainee = in_name
        train_dt = tr_date   ## .strftime('%Y%m%d')
        trainer = in_trainer
        
        insert_train(trainee, train_dt, trainer)
        
        df = read_train(start_date, end_date)
        placeholder.dataframe(df[cols], use_container_width=True, column_config=col_config)
        st.success(f"레슨 일정이 등록되었습니다. {trainee} {train_dt.strftime('%Y-%m-%d %a')}")


## 기존 신청 취소 (개인) ############################################################

def main_cancel():

    if not check_access():
        return
    
    in_name = st.text_input(label='취소할 회원이름을 입력하세요', value=st.session_state.trainee, disabled=not st.session_state.admin_flag)
    
    select_date=st.date_input(label="기준 일자를 선택하세요.", min_value=datetime.date.today(), max_value=datetime.date.today() + datetime.timedelta(weeks=1))
    
    w = select_date.strftime('%w')
    start_date=select_date - datetime.timedelta(days=int(w))
    end_date=select_date + datetime.timedelta(days=(6-int(w)))
        
    df = read_train(start_date, end_date)
    
    if len(df) <= 0:
        st.warning('데이터가 없습니다.')
        return
    else:
        df = df[(df['TRAINEE']==in_name) & (df['CONFIRM_FLAG'].isin(['신청','취소']))].copy()
        if len(df) <= 0:
            st.warning('데이터가 없습니다.')
            return
    
    selected = dataframe_with_selections(df[cols])
    st.write(str(len(selected))+" 명 선택되었습니다.")
    st.dataframe(selected, use_container_width=True, hide_index=True, column_config=col_config)

    if st.button(label='취소', type='primary'):
        cancel_train(selected)
        



## 강습완료 확정 화면 (관리자용) ############################################################

def main_confirm():

    if not check_admin_access():
        return
    
    in_date=st.date_input(label="강습일을 선택하세요.", min_value=datetime.date.today(),
                          max_value=datetime.date.today() + datetime.timedelta(weeks=1) )
  
    df = read_train(in_date, in_date)
    
    if len(df) < 1:
        st.warning('데이터가 없습니다.')
        st.stop()
    else:
        df = df[df['CONFIRM_FLAG'].isin(['신청','확정'])].copy()
        if len(df) <= 0:
            st.warning('데이터가 없습니다.')
            st.stop()
            return
        
    selected = dataframe_with_selections(df[cols])
    
    st.dataframe(selected, use_container_width=True, column_config=col_config)
    st.write(str(len(selected))+" 명 선택되었습니다.")
    
    if st.button(label='확정', type='primary'):
        confirm_train(selected, '확정')
    


## 신청자 강습 완료 화면 (관리자용) ############################################################
     
def main_complete():
    
    if not check_admin_access():
        return
    
    in_date=st.date_input(label="강습일을 선택하세요.", key='main_complete_in_date',
                           min_value=datetime.date.today() - datetime.timedelta(weeks=2),
                           max_value=datetime.date.today())
    
    df = read_train(in_date, in_date)
    
    if len(df) < 1:
        st.warning('데이터가 없습니다.')
        st.stop() 
    else:
        df = df[df['CONFIRM_FLAG'].isin(['확정','완료'])].copy()
        if len(df) <= 0:
            st.warning('데이터가 없습니다.')
            st.stop()
            return
        
    selected = dataframe_with_selections(df[cols])
    st.dataframe(selected, use_container_width=True, column_config=col_config)
    st.write(str(len(selected))+" 명 선택되었습니다.")
    
    if st.button(label='완료', type='primary'):
        confirm_train(selected, '완료')


#####################################################################################
## 메인 프로세스 #####################################################################
#####################################################################################


def main():
    st.sidebar.image('images.jpg')
    menu = ['Home (Login)', '신청현황', '강습신청 - 회원', '신청취소 - 회원', '신청확정 - 운영자', '강습완료 - 운영자']
    
    menu_select = st.sidebar.radio(label="**작업 메뉴를 선택하세요.**", options=menu)
    

    if menu_select==menu[0]:                       ## main_query, main_regist, main_update, main_confirm
        st.header("Edge 강습 신청을 위해 로그인 하세요 ~")
        main_home()

        if 'trainee' in st.session_state:
            if st.session_state.admin_flag:
                st.subheader(f"{st.session_state.trainee} 님은 관리자로 로그인되었습니다.")
            else:
                st.subheader(f"{st.session_state.trainee} 님 로그인 되었습니다.")
            
    elif menu_select==menu[1]:
        st.subheader(f"강습 신청현황을 조회합니다. ")
        main_query()

    elif menu_select==menu[2]:
        st.subheader(f"강습을 신청합니다. ")
        main_regist()    

    elif menu_select==menu[3]:
        st.subheader(f"기존에 신청한 강습을 취소합니다. ")
        main_cancel()
        
    elif menu_select == menu[4]:
        st.subheader(f"신청한 강습을 확정합니다. ")
        main_confirm()
            
    elif menu_select == menu[5]:
        st.subheader(f"강습 여부를 완료처리합니다. ")     
        main_complete()
            
    else:
        st.subheader("선택 오류 입니다.")
        

if __name__ == "__main__":
    main()

 
 
