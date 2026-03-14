# 增加高级搜索功能
# 增加点击头衔、名字、设精人、日期等跳转搜索相关内容的功能

import streamlit as st
import pandas as pd
import os
from urllib.parse import quote

st.set_page_config(page_title="精华消息检索", layout="wide")
st.title("📚 精华消息检索系统")

# 定义本地路径前缀和 GitHub raw 前缀
LOCAL_PREFIX = r"D:\OneDrive\心台\台群精页"
GITHUB_RAW_PREFIX = "https://raw.githubusercontent.com/JaneMoon5/taisJingYe_app/main"

st.markdown("""
<style>
.search-link {
    color: black !important;
    text-decoration: none;
}
.search-link:hover {
    text-decoration: underline;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv('taisJingYe.csv', encoding='utf-8-sig')
    df['日期'] = pd.to_datetime(df['日期'])
    return df

df = load_data()

# 初始化会话状态
if 'search_mode' not in st.session_state:
    st.session_state.search_mode = "普通检索"
if 'adv_title' not in st.session_state:
    st.session_state.adv_title = ""
if 'adv_name' not in st.session_state:
    st.session_state.adv_name = ""
if 'adv_content' not in st.session_state:
    st.session_state.adv_content = ""
if 'adv_setjingren' not in st.session_state:
    st.session_state.adv_setjingren = ""
if 'start_date' not in st.session_state:
    st.session_state.start_date = df['日期'].min().date()
if 'end_date' not in st.session_state:
    st.session_state.end_date = df['日期'].max().date()

# 处理 URL 参数
params = st.query_params
mode_changed = False

# 处理日期参数
if "date" in params:
    try:
        target_date = pd.to_datetime(params["date"][0]).date()
        st.session_state.start_date = target_date
        st.session_state.end_date = target_date
        st.query_params.clear()
    except:
        pass

# 处理高级检索参数
if "adv_title" in params:
    st.session_state.adv_title = params["adv_title"][0]
    mode_changed = True
if "adv_name" in params:
    st.session_state.adv_name = params["adv_name"][0]
    mode_changed = True
if "adv_content" in params:
    st.session_state.adv_content = params["adv_content"][0]
    mode_changed = True
if "adv_setjingren" in params:
    st.session_state.adv_setjingren = params["adv_setjingren"][0]
    mode_changed = True
if mode_changed:
    st.session_state.search_mode = "高级检索"
    st.query_params.clear()

# ---------- 侧边栏 ----------
st.sidebar.header("🔍 检索条件")

search_mode = st.sidebar.radio(
    "选择检索模式",
    ["普通检索", "高级检索"],
    index=0 if st.session_state.search_mode == "普通检索" else 1,
    key="search_mode_radio"
)
st.session_state.search_mode = search_mode

if search_mode == "普通检索":
    search_term = st.sidebar.text_input("关键词（在头衔、名字、内容、设精人中搜索）")
else:
    st.sidebar.markdown("高级检索（留空表示不限制）")
    kw_title = st.sidebar.text_input("头衔关键词", value=st.session_state.adv_title)
    kw_name = st.sidebar.text_input("名字关键词", value=st.session_state.adv_name)
    kw_content = st.sidebar.text_input("内容关键词", value=st.session_state.adv_content)
    kw_setjingren = st.sidebar.text_input("设精人关键词", value=st.session_state.adv_setjingren)
    search_term = None

# 格式多选
format_options = sorted(df['格式'].unique().tolist())
selected_formats = st.sidebar.multiselect("格式", format_options, default=None)

# 日期范围
st.sidebar.subheader("📅 日期范围")
start_date = st.sidebar.date_input("开始日期", st.session_state.start_date)
end_date = st.sidebar.date_input("结束日期", st.session_state.end_date)
st.session_state.start_date = start_date
st.session_state.end_date = end_date

# ---------- 筛选 ----------
filtered_df = df.copy()

if search_mode == "普通检索" and search_term:
    text_cols = ['头衔', '名字', '内容', '设精人']
    mask = filtered_df[text_cols].apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1
    )
    filtered_df = filtered_df[mask]
elif search_mode == "高级检索":
    if kw_title:
        filtered_df = filtered_df[filtered_df['头衔'].astype(str).str.contains(kw_title, case=False, na=False)]
    if kw_name:
        filtered_df = filtered_df[filtered_df['名字'].astype(str).str.contains(kw_name, case=False, na=False)]
    if kw_content:
        filtered_df = filtered_df[filtered_df['内容'].astype(str).str.contains(kw_content, case=False, na=False)]
    if kw_setjingren:
        filtered_df = filtered_df[filtered_df['设精人'].astype(str).str.contains(kw_setjingren, case=False, na=False)]

if selected_formats:
    filtered_df = filtered_df[filtered_df['格式'].isin(selected_formats)]

filtered_df = filtered_df[
    (filtered_df['日期'].dt.date >= start_date) & 
    (filtered_df['日期'].dt.date <= end_date)
]

st.write(f"共找到 **{len(filtered_df)}** 条记录")

# ---------- 图片处理 ----------
def get_image_url(img_path):
    if os.path.exists(img_path):
        return img_path
    normalized = img_path.replace('\\', '/')
    local_norm = LOCAL_PREFIX.replace('\\', '/')
    if normalized.startswith(local_norm):
        relative = normalized[len(local_norm):].lstrip('/')
        return f"{GITHUB_RAW_PREFIX}/{relative}"
    return None

def make_search_link(field, value):
    encoded = quote(str(value))
    return f"?{field}={encoded}"

# ---------- 展示 ----------
if filtered_df.empty:
    st.info("没有找到符合条件的记录")
else:
    for idx, row in filtered_df.iterrows():
        cols = st.columns(5)
        with cols[0]:
            st.markdown(
                f'<a href="{make_search_link("adv_title", row["头衔"])}" target="_self" class="search-link">头衔：<strong>{row["头衔"]}</strong></a>',
                unsafe_allow_html=True
            )
        with cols[1]:
            st.markdown(
                f'<a href="{make_search_link("adv_name", row["名字"])}" target="_self" class="search-link">名字：<strong>{row["名字"]}</strong></a>',
                unsafe_allow_html=True
            )
        with cols[2]:
            date_str = row['日期'].strftime('%Y-%m-%d')
            st.markdown(
                f'<a href="?date={date_str}" target="_self" class="search-link">日期：<strong>{date_str}</strong></a>',
                unsafe_allow_html=True
            )
        with cols[3]:
            st.markdown(
                f'<a href="{make_search_link("adv_setjingren", row["设精人"])}" target="_self" class="search-link">设精人：<strong>{row["设精人"]}</strong></a>',
                unsafe_allow_html=True
            )
        with cols[4]:
            st.markdown(f"设精日期： **{row['设精日期']}**")

        if row['格式'] == '图片':
            img_url = get_image_url(row['内容'])
            if img_url:
                col_img, _ = st.columns([1, 2])
                col_img.image(img_url, use_container_width=True)
            else:
                st.error(f"❌ 无法显示图片：{row['内容']}")
        else:
            st.markdown(row['内容'])

        st.markdown("<hr style='margin:12px 0; opacity:0.3;'>", unsafe_allow_html=True)
        
# 在终端中，进入 app.py 所在目录，执行：
#                                   streamlit run app.py