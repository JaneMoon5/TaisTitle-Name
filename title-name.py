import streamlit as st
import pandas as pd
import os
import hashlib
import json
from io import StringIO
from pypinyin import lazy_pinyin
import streamlit.components.v1 as components

# ----------------------------
# 页面配置
# ----------------------------

st.set_page_config(page_title="头衔·名字图谱", layout="wide")

# 设置侧边栏宽度
st.markdown(
"""
<style>

section[data-testid="stSidebar"]{
    width:220px !important;
}

div[data-testid="stSidebarNav"]{
    width:220px !important;
}

section.main{
    margin-left:220px !important;
}

</style>
""",
unsafe_allow_html=True
)

st.title("📊 头衔 · 名字可视化系统")

# ----------------------------
# 读取CSV
# ----------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "title-name.csv")

try:
    df = pd.read_csv(csv_path)
except:
    st.error("未找到 title-name.csv")
    st.stop()

if df.shape[1] < 2:
    st.error("CSV必须至少两列")
    st.stop()

df = df.iloc[:, :2]
df.columns = ["头衔", "名字"]

df = df.dropna()

# -----------------------------
# 侧边栏
# -----------------------------
with st.sidebar:

    st.header("🔍 搜索")

    search_name = st.text_input("搜索名字")

# ----------------------------
# 解析名字
# ----------------------------
def split_names(x):
    return [n.strip() for n in str(x).split(",") if n.strip()]

df["名字列表"] = df["名字"].apply(split_names)

# 展开
expanded = df.explode("名字列表")

# 统一列名
expanded["名字"] = expanded["名字列表"]

expanded = expanded[["头衔", "名字"]]


# grouped = expanded.groupby("头衔")["名字"].apply(list).reset_index()

# ----------------------------
# 拼音排序
# ----------------------------

expanded = expanded.sort_values(
    by="头衔",
    key=lambda col: col.map(lambda x: "".join(lazy_pinyin(x)))
)

# -----------------------------
# 表格数据
# -----------------------------
grouped = expanded.groupby("头衔")["名字"].apply(list).reset_index()

max_len = grouped["名字"].apply(len).max()

table_data = []

for _,row in grouped.iterrows():

    r = [row["头衔"],len(row["名字"])] + row["名字"]

    r += [""]*(max_len-len(row["名字"]))

    table_data.append(r)

columns = ["头衔","名字个数"] + [f"名字{i+1}" for i in range(max_len)]

table_df = pd.DataFrame(table_data,columns=columns)

# -----------------------------
# 节点颜色
# -----------------------------
def name_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest()[:6],16)%360
    return f"hsl({h},70%,60%)"

# ----------------------------
# 构建图数据
# ----------------------------

nodes = []
edges = []

title_set = set()
name_set = set()

for _, row in expanded.iterrows():

    title = row["头衔"]
    name = row["名字"]

    if title not in title_set:
        nodes.append({
            "id": f"title_{title}",
            "name": title,
            "symbol": "rect",
            "symbolSize": [60,30],
            "itemStyle": {
                "color": "#ffffff",
                "borderColor": "#888",
                "borderWidth": 2
            }
        })
        title_set.add(title)

    if name not in name_set:
        nodes.append({
            "id": f"name_{name}",
            "name": name,
            "symbol": "circle",
            "symbolSize": 28,
            "itemStyle": {
                "color": name_color(name)
            }
        })
        name_set.add(name)

    edges.append({
        "source": f"title_{title}",
        "target": f"name_{name}"
    })

# -----------------------------
# 页面布局
# -----------------------------
col1,col2=st.columns([2,3])

# 左侧表格
with col1:

    st.subheader("📋 头衔列表")

    html_table = table_df.to_html(index=False, border=0)

    html_code = f"""
    <style>
    .table-container {{
        overflow:auto;
        height:650px;
        border:1px solid #e6e6e6;
        border-radius:6px;
    }}

    /* 表格基础样式 */
    table {{
        border-collapse: collapse;
        width:100%;
        font-size:13px;
    }}

    th, td {{
        padding:6px 10px;
        border-bottom:1px solid #eee;
        white-space: nowrap;
        text-align:left;
    }}

    /* 表头固定并添加阴影 */
    th {{
        background:#f6f7fb;
        position: sticky;
        top: 0;
        z-index:3;
        font-weight:600;
        box-shadow:0 2px 4px rgba(0,0,0,0.08);
    }}

    /* 固定列 */
    th:first-child,
    td:first-child {{
        position: sticky;
        left: 0;
        background:#f6f7fb;
        z-index:4;
        font-weight:600;
        box-shadow:3px 0 6px rgba(0,0,0,0.08);
    }}

    /* 左上角格子层级最高 */
    th:first-child {{
        z-index:5;
    }}

    /* hover 高亮 */
    tr:hover td {{
        background:#f7f9fc;
    }}
    
    </style>

    <div class="table-container">
    {html_table}
    </div>
    """

    components.html(
        html_code,
        height=680,
        scrolling=True
    )


# -----------------------------
# 右侧图谱
# -----------------------------
with col2:

    st.subheader("🕸 关系图")

    nodes_json=json.dumps(nodes,ensure_ascii=False)
    edges_json=json.dumps(edges,ensure_ascii=False)

    highlight = search_name if search_name else ""

    html=f"""
    <html>
    <head>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    </head>

    <body>

    <div style="margin-bottom:8px">
    <button onclick="download()">导出PNG</button>
    </div>

    <div id="chart" style="width:100%;height:720px;"></div>

    <script>

    var nodes={nodes_json};
    var links={edges_json};

    var highlight="{highlight}";

    nodes.forEach(function(n){{
        if(highlight && n.name.includes(highlight)){{
            n.itemStyle={{
                color:"#ff4b4b",
                borderWidth:4
            }}
        }}
    }});

    var chart=echarts.init(document.getElementById('chart'));

    var option={{

        tooltip:{{}},

        series:[{{

            type:'graph',

            layout:'force',

            roam:true,

            emphasis:{{focus:'adjacency'}},

            force:{{
                repulsion:320,
                edgeLength:120
            }},

            label:{{
                show:true
            }},

            lineStyle:{{
                color:'#aaa'
            }},

            data:nodes,

            links:links

        }}]

    }};

    chart.setOption(option);

    function download(){{
        var url=chart.getDataURL({{
            type:'png',
            pixelRatio:2,
            backgroundColor:'#fff'
        }});
        var a=document.createElement("a");
        a.href=url;
        a.download="graph.png";
        a.click();
    }}

    </script>

    </body>
    </html>
    """

    components.html(html,height=750)

st.subheader("📊 统计")

c1, c2, c3 = st.columns(3)

with c1:
        st.metric("头衔数量", len(title_set))

with c2:
        st.metric("名字数量", len(name_set))

with c3:
        st.metric("关系数量", len(edges))
        
st.caption("方块 = 头衔 | 圆形 = 名字 | 搜索可高亮 | 可导出PNG")