from flask import session
import streamlit as st
import pandas as pd
import datetime
import bcrypt    # password 암호화
import base64    #  passwordd 암호화
import json
import os
import logging


## 기본 공통 변수 선언  ########################################################

st.session_state.member_path ="./edge_members.json"
st.session_state.train_plan_path = "./edge_train_plans.csv"
st.session_state.cols = ['강습일','회원명','코치명','상태','입력일']

## column 이름 및 포맷 변경
col_config={'강습일': st.column_config.DateColumn( format="MM-DD ddd"),
            '입력일': st.column_config.DateColumn(format="MM-DD HH:mm"),
}
    
## 로그 화일 생성  ########################################################

def create_logger():

    logger = logging.getLogger(os.path.basename(__file__))   ## logger name으로 생성/참조

    if len(logger.handlers) > 0:
        return logger
    
    # Set the log level
    logger.setLevel(logging.DEBUG)

    # Create a file handler and set the log level
    file_handler = logging.FileHandler('edge.log', encoding='utf-8', mode='at')
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter and add it to the file handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(lineno)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)
    return logger


logger = create_logger()    ## log instance 시작

## 함수 선언 ########################################################

## json 화일 읽기

def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    except Exception as e:
        if 'No such file' in str(e):
            write_json(file_path,{})
            return {}
        st.error(e)
        return {}
    
## json 화일 쓰기

def write_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        
    except Exception as e:
        st.error(f"JSON 파일 쓰기에 실패했습니다.{file_path}")
        return False

## 강습신청 현황 조회 ######################################################################

def read_train(sd:datetime, ed:datetime):
    
    sd = sd.strftime('%Y-%m-%d')
    ed = ed.strftime('%Y-%m-%d')

    if not os.path.exists(st.session_state.train_plan_path):
        with open(st.session_state.train_plan_path, 'wt', encoding='utf-8') as f:    ## 새로운 파일 만들기
            f.writelines(','.join(st.session_state.cols)+'\n')     ## 새로운 파일에 컬럼명 넣기

    try:
        df = pd.read_csv(st.session_state.train_plan_path)
        st.session_state.train_plan = df     ## 전체 신청현황을 저장

    except Exception as e:
        st.error(e)
        return False
    
    df = df[(df['강습일'] >= sd) & (df['강습일'] <= ed)].reset_index(drop=True)
    df.index += 1

    return df

## 강습일정 입력 ###################################################

def insert_train(trainee: str, train_dt: datetime, trainer:str):    ## cols = ['강습일','회원명','코치명','상태','입력일']
    
    ll = [[train_dt.strftime('%Y-%m-%d'), trainee, trainer, '신청', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]

    df=pd.concat([st.session_state.train_plan, pd.DataFrame(data=ll, columns=st.session_state.cols)], ignore_index=True)

    df.sort_values(['강습일','회원명','입력일'], inplace=True)
    df.drop_duplicates(subset=['강습일','회원명'], keep='last', inplace=True)

    df.to_csv(st.session_state.train_plan_path, index=False)
    
    return True


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

    df = df[df['상태']=='신청']

    for ii in range(len(df)):
        ll = [[df.iloc[ii]['강습일'], df.iloc[ii]['회원명'], df.iloc[ii]['코치명'], '취소',
               datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
        logger.info(f"등록취소 : {df.iloc[ii]['회원명']} : {df.iloc[ii]['강습일']}")
                        
        st.session_state.train_plan=pd.concat([st.session_state.train_plan, pd.DataFrame(data=ll, columns=st.session_state.cols)], ignore_index=True)

    st.session_state.train_plan.sort_values(['강습일','회원명','입력일'], inplace=True)
    st.session_state.train_plan.drop_duplicates(subset=['강습일','회원명'], keep='last', inplace=True)

    st.session_state.train_plan.to_csv(st.session_state.train_plan_path, index=False)
    st.session_state.train_plan = pd.read_csv(st.session_state.train_plan_path)
    
    st.success(str(len(df))+'명 취소되었습니다. (신청 상태만 취소됩니다.)')
    return True

## 신청한 강습 요청에 대해 일정 확정 ###################################################
    
def confirm_train(df: pd.DataFrame, work_gbn: str):
    

    for ii in range(len(df)):
        ll = [[df.iloc[ii]['강습일'], df.iloc[ii]['회원명'], df.iloc[ii]['코치명'], work_gbn,
               datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]
        logger.info(f"{work_gbn} : {df.iloc[ii]['회원명']} : {df.iloc[ii]['강습일']}")
                        
        st.session_state.train_plan=pd.concat([st.session_state.train_plan, pd.DataFrame(data=ll, columns=st.session_state.cols)], ignore_index=True)

    st.session_state.train_plan.sort_values(['강습일','회원명','입력일'], inplace=True)
    st.session_state.train_plan.drop_duplicates(subset=['강습일','회원명'], keep='last', inplace=True)

    st.session_state.train_plan.to_csv(st.session_state.train_plan_path, index=False)
    st.session_state.train_plan = pd.read_csv(st.session_state.train_plan_path)
    
    st.success(str(len(df))+' 명 '+ work_gbn + ' 처리 되었습니다')
    return True
    
## 화일 잠금 ###############################################################

def lock_file(f_path, w_gbn):    ## 신청, 취소, 확정, 완료
    if os.path.exists(f_path):
        st.error('잠시 후 재시도 하세요.')
        
        return False
    else:
        with open(f_path, 'wt', encoding='utf-8') as f:
            if 'trainee' in st.session_state:
                f.write(f"{str(datetime.datetime.now())} {st.session_state.trainee} : {w_gbn}")
            else:
                f.write(f"{str(datetime.datetime.now())} 무명씨 : {w_gbn}")
            return True


## 화일 잠금 해제 ###########################################################
def unlock_file(f_path):
    if os.path.exists(f_path):
        os.remove(f_path)

## dataframe selected ###################################################

def dataframe_with_selections(df: pd.DataFrame):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "선택", False)

    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        use_container_width=True,
        column_config={"선택": st.column_config.CheckboxColumn(required=True),
                       '강습일': st.column_config.DateColumn(format="MM-DD ddd"),
                       '입력일': st.column_config.DateColumn(format="MM-DD HH:MM")},
        disabled=df.columns,
    )
    # Filter the dataframe using the temporary column
    selected_rows = edited_df[edited_df["선택"]]
    
    return selected_rows.drop("선택", axis=1)


## 첫 화면 로그인 처리 #################################################################

def login_session(in_name: str, in_pwd: str):

    if 'members' in st.session_state:
        del st.session_state.members
        
    if 'trainee' in st.session_state:
        del st.session_state.trainee
        del st.session_state.admin_flag

    st.session_state.members = read_json(st.session_state.member_path)           

    try:
        pwd = st.session_state.members[in_name]["passwd"]
    
    except KeyError:
        st.warning('등록되지 않은 회원입니다.')
        return False
    
    except Exception as ex:
        st.write(st.session_state.members)
        st.error(str(ex))
        return False
        
    hashed = base64.b64decode(pwd.encode('utf-8'))     ## 비밀번호 비교 확인
    if not bcrypt.checkpw(in_pwd.encode(), hashed):
        st.warning('비밀번호 오류 입니다.')
        return False

    st.session_state.trainee = in_name
    st.session_state.admin_flag = st.session_state.members[in_name]["admin_flag"]

    st.success('로그인 되었습니다.')
    logger.info('로그인 : '+in_name)
    
    return True

## 회원 등록 #################################################################

def insert_trainee(in_name: str, in_pwd: str):

    if 'members' not in st.session_state:
        st.session_state.members = read_json(st.session_state.member_path)           

    if len(in_pwd) < 4:
        st.warning('비밀번호는 4자 이상 입력하세요.')
        return False
    
    hashed = bcrypt.hashpw(in_pwd.encode(), bcrypt.gensalt())
    hashed = base64.b64encode(hashed).decode('utf-8')
  
    st.session_state.members[in_name]={}
    st.session_state.members[in_name]['passwd'] = hashed
    st.session_state.members[in_name]['admin_flag'] = 0
    
    try:
        write_json(st.session_state.member_path, st.session_state.members)

    except Exception as ex:
        st.error(str(ex))
        return False
    
    st.success('회원으로 가입되었습니다.' + in_name)
    logger.info('회원가입 : '+in_name)
    
    return True
    
## 비밀 번호 변경 #################################################################

def change_passwd(in_name: str, in_pwd: str):

    hashed = bcrypt.hashpw(in_pwd.encode(), bcrypt.gensalt())
    hashed = base64.b64encode(hashed).decode('utf-8')

    st.session_state.members[in_name]['passwd'] = hashed
    
    try:
        write_json(st.session_state.member_path, st.session_state.members)

    except Exception as ex:
        st.error(str(ex))
        return False
    
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
    
    in_name = st.text_input(label="이름을 입력하세요.")
    in_pwd = st.text_input(label='비밀번호를 입력하세요', type='password')

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button(label='로그인', type='primary'):
            login_session(in_name, in_pwd)
    
    if 'trainee' not in st.session_state:
        with col2:
            if st.button(label='회원 가입'):
                if lock_file('member.lock','가입'):
                    insert_trainee(in_name, in_pwd)
                    unlock_file('member.lock')

    if 'trainee' in st.session_state:
        with col3:
            if st.button(label='비밀번호 변경'):
                if lock_file('member.lock','비번'):
                    change_passwd(in_name, in_pwd)
                    unlock_file('member.lock')  
    

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
        else:
            st.dataframe(df,  use_container_width=True, column_config=col_config)
            st.write(str(len(df))+'명 조회되었습니다.')


## 신규 강습 신청 (개인) ############################################################

def main_regist():

    if not check_access():
        return
    
    in_date=st.date_input(label="신청 기준일", disabled=True, help='신청 기준일 이후 화/목요일')   
    
    rdo_train_date = st.radio(label="강습 일자를 선택하세요.", options=train_day_list(in_date), horizontal=True) 
    tr_date = datetime.datetime.strptime(rdo_train_date[:10], '%Y/%m/%d')
    
    df = read_train(tr_date, tr_date)
    placeholder=st.empty()

    if len(df) > 0:
        placeholder.dataframe(df, use_container_width=True, column_config=col_config)
    else:
        st.warning('아직 신청한 사람이 없습니다.')

    in_name = st.text_input(label="강습받을 회원 이름을 입력하세요.", value=st.session_state.trainee, disabled=not st.session_state.admin_flag)
    in_trainer = st.radio(label="강사를 선택하세요.", options=['구코치','신코치'], horizontal=True) 

    if st.button('저장', key='main_regist_btn', type='primary'):

        if lock_file('plan.lock', '신청'):     
            insert_train(in_name, tr_date, in_trainer)
            unlock_file('plan.lock')
            st.success(f"레슨 일정이 등록되었습니다. {in_name} : {tr_date.strftime('%Y-%m-%d')}")
            logger.info(f"일정등록 : {in_name} : {tr_date.strftime('%Y-%m-%d')}")
        
        df = read_train(tr_date, tr_date)
        placeholder.dataframe(df, use_container_width=True, column_config=col_config)

        

## 기존 신청 취소 (개인) ############################################################

def main_cancel():

    if not check_access():
        return
    
    in_name = st.text_input(label='취소할 회원이름을 입력하세요', value=st.session_state.trainee, disabled=not st.session_state.admin_flag)
    in_date=st.date_input(label="강습 일자를 선택하세요.", min_value=datetime.date.today() - datetime.timedelta(weeks=1), max_value=datetime.date.today() + datetime.timedelta(weeks=1))
    
    df = read_train(in_date, in_date)
    df = df[df['회원명']==in_name].reset_index(drop=True)
    
    if len(df) <= 0:
        st.warning('데이터가 없습니다.')
        return
    
    selected = dataframe_with_selections(df)
    st.write(str(len(selected))+" 명 선택되었습니다.")
    st.dataframe(selected, use_container_width=True, hide_index=True, column_config=col_config)

    if st.button(label='취소', type='primary'):
        if lock_file('plan.lock', '취소'):
            cancel_train(selected)
            unlock_file('plan.lock')
        

## 신청자 완료 화면 (관리자용) ############################################################
     
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
            
    selected = dataframe_with_selections(df)
    st.dataframe(selected, use_container_width=True, column_config=col_config)
    st.write(str(len(selected))+" 명 선택되었습니다.")
    
    if st.button(label='완료', type='primary'):
        if lock_file('plan.lock', '완료'):
            confirm_train(selected, '완료')
            unlock_file('plan.lock')


## 강습완료 확정 화면 (관리자용) ############################################################

def main_confirm():

    if not check_admin_access():
        return
    
    in_date=st.date_input(label="강습일을 선택하세요.", min_value=datetime.date.today() - datetime.timedelta(weeks=2),
                          max_value=datetime.date.today() + datetime.timedelta(weeks=1) )
  
    df = read_train(in_date, in_date)
    if len(df) < 1:
        st.warning('데이터가 없습니다.')
        st.stop()
        
    selected = dataframe_with_selections(df)
    
    st.dataframe(selected, use_container_width=True, column_config=col_config)
    st.write(str(len(selected))+" 명 선택되었습니다.")
    
    if st.button(label='확정', type='primary'):
        if lock_file('plan.lock', '확정'):
            confirm_train(selected, '확정')
            unlock_file('plan.lock')
    

#####################################################################################
## 메인 프로세스 #####################################################################
#####################################################################################


def main():
    
    st.sidebar.image('images.jpg')
    
    menu = ['Home (Login)', '신청현황 조회', '신규강습 신청 - 회원', '기존신청 취소 - 회원', '신청 확정 - 운영자', '강습 완료 - 운영자']
    
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

 
