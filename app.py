import streamlit as st
import pandas as pd

view=[100,150,300]
st.write('# 유투브 조회수')
view
st.write('## 바차트')
st.bar_chart(view)

ss=pd.Series(view)
ss


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

# import cryptography

############################# DB접속경로
db_config_vdi = {
    'user' : 'daechul',
    'password' : 'rootpwd',
    'host' : 'localhost',
    'port' : 3306,
    'database' : 'dcdb',
    'charset' : 'utf8'
}

db_config_pc = {
    'user' : 'root',
    'password' : 'daechul',
    'host' : 'localhost',
    'port' : 3306,
    'database' : 'dcdb',
    'charset' : 'utf8'
}
def create_db_connection():
    db_conn = pymysql.connect(**db_config_vdi)
    ##conn = pymysql.connect(**db_config_pc)
    return db_conn


## 강습신청 현황 조회 ######################################################################

def read_train(sd:datetime, ed:datetime):
    db_conn = create_db_connection()
    curs = db_conn.cursor()

    sql = "SELECT * FROM train_plan where date(train_dt) between date(%s) and date(%s) order by train_dt, update_dt"
    
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

    cols = [desc[0] for desc in curs.description]     ## 컬럼 이름 가져오기
    df = pd.DataFrame(result, columns=cols)
    
    df['TRAIN_DT'] = pd.to_datetime(df['TRAIN_DT'])
    df['TRAIN_DAY'] = df['TRAIN_DT'].dt.strftime('%a')
    df['강습일'] = df['TRAIN_DT'].dt.strftime('%m-%d') + ' ' + df['TRAIN_DAY']
    df['수정일시'] = df['UPDATE_DT'].dt.strftime('%m-%d %H:%M:%S')
    
    df.index = df.index + 1

    return df


## 강습일정 입력 ###################################################

def insert_train(trainee: str, train_dt: str, trainer:str):
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
            st.error(f"이미 신청되었습니다.  {trainee} - {train_dt}")
        elif '1452' in str(ex):
            st.error(f"먼저 회원 등록바랍니다.  {trainee} ")
        else:
            st.error(str(ex))
        st.stop()
      
    finally:
        curs.close()
        db_conn.close()


## 요청일자 이후로 금주/차주 강습 가능한 일정 선택  ###################################################

def train_day_list(tr_date: datetime):
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

    for ii in range(len(df)):
        sql = "UPDATE train_plan Set CONFIRM_FLAG = '취소', UPDATE_DT = CURRENT_TIMESTAMP \
            where train_dt = %s and TRAINEE = %s and confirm_flag is null"   
            
        val = (df.iloc[ii].TRAIN_DT, df.iloc[ii].TRAINEE)    
                
        try:    
            curs.execute(sql, val)
            db_conn.commit()

        except Exception as ex:
            db_conn.rollback()
            st.error(str(ex))
            st.stop()
                            
    curs.close()
    db_conn.close()
    
    st.success(str(len(df))+'건 취소되었습니다')


## 신청한 강습 요청에 대해 일정 확정 ###################################################
    
def confirm_train(df: pd.DataFrame, work_gbn: str):
    db_conn = create_db_connection()
    curs = db_conn.cursor()
  
    for ii in range(len(df)):
        sql = "UPDATE train_plan Set CONFIRM_FLAG = %s where train_dt = %s and TRAINEE = %s"
        val = (work_gbn, df.iloc[ii].TRAIN_DT, df.iloc[ii].TRAINEE)    
                
        try:    
            curs.execute(sql, val)
            db_conn.commit()

        except Exception as ex:
            db_conn.rollback()
            st.error(str(ex))
            st.stop()

    curs.close()
    db_conn.close()
    st.success(str(len(df))+' 건 '+ work_gbn + ' 처리 되었습니다')
    

## dataframe selected ###################################################

def dataframe_with_selections(df: pd.DataFrame):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
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
        result = curs.fetchall()
    
    except Exception as ex:
        st.error(str(ex))
        st.stop()
    
    finally:
        curs.close()
        db_conn.close()

    if not result:
        st.error('등록된 코치가 없습니다')
        
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
        result = curs.fetchone()
    
    except Exception as ex:
        st.error(str(ex))
        st.stop()

    finally:
        curs.close()
        db_conn.close()
    
    if not result:
        st.warning('등록되지 않은 회원입니다.')
        return False                     ## 회원가입 프로세스 처리를 위해  return false 함
        
    hashed = base64.b64decode(result[1].encode('utf-8'))     ## 비밀번호 비교 확인
    if not bcrypt.checkpw(in_pwd.encode(), hashed):
        st.warning('비밀번호 오류 입니다.')
        st.stop()

    st.session_state.trainee = result[0]
    st.session_state.admin_flag = result[2]

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
        db_conn.commit()
        
    except Exception as ex:
        db_conn.rollback()
        if '1062' in str(ex):
            st.error(f"이미 신청되었습니다.  {in_name}")
        else:
            st.error(str(ex))
        return False
    
    finally:
        curs.close()
        db_conn.close()

    st.success('가입되었습니다.')
    
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
        db_conn.commit()

    except Exception as ex:
        db_conn.rollback()
        st.error(str(ex))
        st.stop()

    finally:
        curs.close()
        db_conn.close()
        
    st.success(in_name + ' 비밀번호가 변경 되었습니다.')


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
    if 'in_pwd' not in st.session_state:
        st.session_state.in_pwd = ''

    in_name=st.text_input(label="이름을 입력하세요.", key='main_home_in_name')
    in_pwd=st.text_input(label='비밀번호를 입력하세요', value=st.session_state.in_pwd, type='password', key='main_home_in_pwd')

    if st.button(label='로그인', key='main_home_login_btn'):
        if login_session(in_name, in_pwd):
            st.success('로그인 되었습니다.')
            st.session_state.in_pwd = ''
            
        else:
            st.warning("회원 가입 신청바랍니다.")
            st.session_state.in_pwd = ''    
            st.button(label='가입', key='main_home_join_btn', on_click=insert_trainee, args=(in_name, in_pwd))

    if 'trainee' in st.session_state:
        st.session_state.in_pwd = ''
        st.button(label='비밀번호 변경', on_click=change_passwd, args=(in_name, in_pwd))


## 신청현황 조회 ############################################################

def main_query():
    
    if not check_access():
        return
    
    yw=datetime.datetime.today().strftime('%Y%W')

    rdo_scope = st.radio("조회범위를 선택하세요", ["하루", "한주", "기간"], horizontal=True)

    match rdo_scope:
        case '하루':
            start_date = st.date_input(label="조회할 일자를 선택하세요.", key='main_query_in_date', min_value=datetime.date.today() - datetime.timedelta(weeks=4),
                                     max_value=datetime.date.today() + datetime.timedelta(weeks=1))
            end_date = start_date

        case '한주':
            select_date=st.date_input(label="조회할 기준일자를 선택하세요.", key='main_query_in_date', min_value=datetime.date.today() - datetime.timedelta(weeks=4),
                                     max_value=datetime.date.today() + datetime.timedelta(weeks=1))
            
            w = select_date.strftime('%w')
            start_date=select_date - datetime.timedelta(days=int(w))
            end_date=select_date + datetime.timedelta(days=(6-int(w)))

        case '기간':
            start_date=st.date_input(label="시작 일자를 선택하세요.", key='main_query_in_start', min_value=datetime.date.today() - datetime.timedelta(weeks=52),
                                     max_value=datetime.date.today())
            
            end_date=st.date_input(label="종료 일자를 선택하세요.", key='main_query_in_end', min_value=datetime.date.today(),
                                     max_value=datetime.date.today() + datetime.timedelta(weeks=1))

        case _:
            st.error("조회 범위선택 오류")

    if st.button(label="조회", key='main_query_btn'):    
        df = read_train(start_date, end_date)
        if len(df) < 1:
            st.warning("조회범위에 데이터가 없습니다.")
            st.stop()

        df['CONFIRM_FLAG']=df['CONFIRM_FLAG'].fillna('')

        cols = ['강습일',  'TRAINER', 'TRAINEE', '수정일시', 'CONFIRM_FLAG']
        st.dataframe(df[cols])
        st.write(str(len(df))+'건 조회되었습니다.')


## 신규 강습 신청 (개인) ############################################################

def main_regist():

    if not check_access():
        return
    
    in_date=st.date_input(label="신청 기준일", key='main_regist_in_date', min_value=datetime.date.today(), max_value=datetime.date.today() + datetime.timedelta(days=6))   
    
    rdo_train_date = st.radio(label="강습 일자를 선택하세요.", options=train_day_list(in_date), horizontal=True) 
    tr_date = datetime.datetime.strptime(rdo_train_date[:10], '%Y/%m/%d')
    
    w = tr_date.strftime('%w')
    start_date, end_date = tr_date, tr_date     
      
    df = read_train(start_date, end_date)
    cols = ['강습일', 'TRAINEE', 'TRAINER', '수정일시', 'CONFIRM_FLAG']

    placeholder=st.empty()

    if len(df) > 0:
        placeholder.table(df[cols])
    else:
        st.warning('아직 신청한 사람이 없습니다.')

    in_name = st.text_input(label="강습받을 회원 이름을 입력하세요.", value=st.session_state.trainee, disabled=True, key='main_regist_in_name')

    rdo_trainer = st.radio(label="강사를 선택하세요.", options=read_trainer(), horizontal=True) 

    if (tr_date.strftime('%w') == '4') & (rdo_trainer == '유남규(구)'):
        st.warning('목요일은 '+rdo_trainer+'코치님은 신청 불가합니다.')
        st.stop()

    in_trainer = rdo_trainer

    if st.button('저장', key='main_regist_btn'):
        trainee = in_name
        train_dt = tr_date.strftime('%Y%m%d')
        trainer = in_trainer
        
        insert_train(trainee, train_dt, trainer)
        
        df = read_train(start_date, end_date)
        placeholder.table(df[cols])
        st.success(f"레슨 일정이 등록되었습니다. {trainee} - {train_dt}")


## 기존 신청 취소 (개인) ############################################################

def main_cancel():

    if not check_access():
        return

    in_date=st.date_input(label="강습일을 선택하세요.", key='main_cancel_in_date', \
                          value='today', min_value=datetime.date.today(), max_value=datetime.date.today() + datetime.timedelta(days=6))

    start_date, end_date = in_date, in_date 
    
    df = read_train(start_date, end_date)

    if len(df) <= 0:
        st.warning('데이터가 없습니다.')
        st.stop()

    cols = ['강습일', 'TRAINEE', 'TRAINER', '수정일시', 'CONFIRM_FLAG', 'TRAIN_DT']
    
    df = df[df['TRAINEE']==st.session_state.trainee].copy()

    selected = dataframe_with_selections(df[cols])
    st.write(str(len(selected))+" 건 선택되었습니다.")
    st.table(selected)
    
    if 'cancel_clicked' not in st.session_state:
        st.session_state.cancel_clicked = False

    if st.button(label='취소', key='main_cancel_btn'):
        st.session_state.cancel_clicked = True
    
    if st.session_state.cancel_clicked:
        cancel_train(selected)

    st.session_state.cancel_clicked = False
        

## 신청자 완료 화면 (관리자용) ############################################################
     
def main_complete():
    
    if not check_admin_access():
        return
    
    in_date=st.date_input(label="강습일을 선택하세요.", key='main_complete_in_date')
                          ## value='today', min_value=datetime.date.today() - datetime.timedelta(days=30), max_value=datetime.date.today() )

    start_date=in_date 
    end_date=in_date      
    
    placeholder=st.empty()
    
    df = read_train(start_date, end_date)
    if len(df) < 1:
        st.warning('데이터가 없습니다.')
        st.stop()

    df.sort_values(by=['TRAIN_DT','TRAINER', 'UPDATE_DT'], inplace=True)
    cols = ['강습일', 'TRAINER',  '수정일시', 'TRAINEE', 'CONFIRM_FLAG', 'TRAIN_DT']
            
    selected = dataframe_with_selections(df[cols])
    st.write(str(len(selected))+" 건 선택되었습니다.")
    st.table(selected)
    
    
    if 'complete_clicked' not in st.session_state:
        st.session_state.complete_clicked = False

    if st.button(label='완료', key='main_complete_btn'):
        st.session_state.complete_clicked = True
    
    if st.session_state.complete_clicked:
        confirm_train(selected, '완료')

    st.session_state.complete_clicked = False 


## 강습완료 확정 화면 (관리자용) ############################################################

def main_confirm():

    if not check_admin_access():
        return
    
    in_date=st.date_input(label="강습일을 선택하세요.", key='main_confirm_in_date')
                          #value='today', min_value=datetime.date.today() - datetime.timedelta(days=6), max_value=datetime.date.today() )

    start_date, end_date = in_date, in_date      
    
    df = read_train(start_date, end_date)
    if len(df) < 1:
        st.warning('데이터가 없습니다.')
        st.stop()

    df.sort_values(by=['TRAIN_DT','TRAINER', 'UPDATE_DT'], inplace=True)
    cols = ['강습일', 'TRAINER', '수정일시', 'TRAINEE', 'CONFIRM_FLAG', 'TRAIN_DT']
        
    selected = dataframe_with_selections(df[cols])
    st.write(str(len(selected))+" 건 선택되었습니다.")
    #st.write(selected)
    st.table(selected)

    if 'confirm_clicked' not in st.session_state:
        st.session_state.confirm_clicked = False

    if st.button(label='확정'):
        st.session_state.confirm_clicked = True
    
    if st.session_state.confirm_clicked:
        confirm_train(selected, '확정')

    st.session_state.confirm_clicked = False 
    

#####################################################################################
## 메인 프로세스 #####################################################################
#####################################################################################


def main():
    menu = ['Home', '신청현황 조회', '신규강습 신청 - 회원', '기존신청 취소 - 회원', '신청 확정 - 운영자', '강습 완료 - 운영자']
    st.sidebar.subheader("작업 메뉴를 선택하세요.")
    menu_select = st.sidebar.radio(label="", options=menu)

    if menu_select==menu[0]:                       ## main_query, main_regist, main_update, main_confirm
        st.header("환영합니다.")
        main_home()
        
    elif menu_select==menu[1]:
        st.subheader(f"강습 신청현황을 조회합니다. -{st.session_state.trainee}-")
        main_query()

    elif menu_select==menu[2]:
        st.subheader(f"강습을 신청합니다. -{st.session_state.trainee}-")
        main_regist()    

    elif menu_select==menu[3]:
        st.subheader(f"기존에 신청한 강습을 취소합니다. -{st.session_state.trainee}-")
        main_cancel()
        
    elif menu_select == menu[4]:
        st.subheader(f"신청한 강습을 확정합니다. -{st.session_state.trainee}-")
        main_confirm()
            
    elif menu_select == menu[5]:
        st.subheader(f"강습 여부를 완료처리합니다. -{st.session_state.trainee}-")     
        main_complete()
            
    else:
        st.subheader("선택 오류 입니다.")
        

if __name__ == "__main__":
    main()

 
