import streamlit as st
import pandas as pd

view=[100,150,300]
st.write('# 유투브 조회수')
view
st.write('## 바차트')
st.bar_chart(view)

ss=pd.Series(view)
ss


ss
