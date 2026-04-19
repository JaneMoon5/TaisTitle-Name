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
csv_path = os.path.join(BASE_DIR, "taisJingYe.csv")
match_path = os.path.join(BASE_DIR, "title-match.csv")   # 新增匹配文件路径
add_path = os.path.join(BASE_DIR, "title-add-name.csv")  # 新增补充文件路径

try:
    df = pd.read_csv(csv_path)
except:
    st.error("未找到taisJingYe.csv")
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

# 去重（避免重复行影响统计）
expanded_unique = expanded.drop_duplicates()


# ----------------------------
# +++ 新增：读取 title-add-name.csv 并合并补充数据 +++
# ----------------------------
if os.path.exists(add_path):
    try:
        add_df_raw = pd.read_csv(add_path, header=None, encoding='utf-8')
        add_records = []
        for _, row in add_df_raw.iterrows():
            title = row[0]
            if pd.isna(title) or str(title).strip() == "":
                continue
            title = str(title).strip()
            # 遍历该行后面的所有列（第二列及以后）
            for col in range(1, len(row)):
                name_val = row[col]
                if pd.isna(name_val):
                    continue
                name = str(name_val).strip()
                if name:
                    add_records.append({"头衔": title, "名字": name})
        if add_records:
            add_df = pd.DataFrame(add_records)
            # 合并并去重（避免重复添加同一头衔下的同一名字）
            expanded_unique = pd.concat([expanded_unique, add_df], ignore_index=True)
            expanded_unique = expanded_unique.drop_duplicates(subset=["头衔", "名字"])
    except Exception as e:
        st.warning(f"读取 title-add-name.csv 时出错: {e}")
else:
    st.info("未找到 title-add-name.csv，将不添加补充名字")

# 重新构建 expanded（唯一边，用于图谱和排序）
expanded = expanded_unique.copy()
    
    
# ----------------------------
# 拼音排序（按头衔）
# ----------------------------

expanded = expanded.sort_values(
    by="头衔",
    key=lambda col: col.map(lambda x: "".join(lazy_pinyin(x)))
)


# ----------------------------
# 读取头衔匹配文件（用于“其他头衔”列）
# ----------------------------
title_groups = []  # 存储每组头衔列表
title_to_others = {}  # 映射：头衔 -> 同组其他头衔列表

if os.path.exists(match_path):
    try:
        with open(match_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 假设每行用逗号分隔头衔
                titles = [t.strip() for t in line.split(',') if t.strip()]
                if len(titles) >= 2:
                    title_groups.append(titles)
                    # 为组内每个头衔记录其他头衔
                    for i, t in enumerate(titles):
                        others = titles[:i] + titles[i+1:]
                        if t not in title_to_others:
                            title_to_others[t] = []
                        title_to_others[t].extend(others)
        # 去重
        for t in title_to_others:
            title_to_others[t] = list(set(title_to_others[t]))
    except Exception as e:
        st.warning(f"读取 title-match.csv 时出错: {e}")
else:
    st.info("未找到 title-match.csv，将不显示头衔匹配信息")
    
    
# -----------------------------
# 表格数据
# -----------------------------

# 先按头衔分组，收集唯一名字列表
grouped = expanded_unique.groupby("头衔")["名字"].apply(list).reset_index()

# 为每个头衔添加“其他头衔”信息
def get_other_titles_html(title):
    others = title_to_others.get(title, [])
    if others:
        # 用 <br> 换行显示多个头衔
        return "<br>".join(others)
    return ""

grouped["其他头衔"] = grouped["头衔"].apply(get_other_titles_html)

# 重新排列列顺序：头衔、其他头衔、名字个数、名字列表
grouped["名字个数"] = grouped["名字"].apply(len)


max_len = grouped["名字"].apply(len).max()

table_data = []

for _,row in grouped.iterrows():

    # 行数据：[头衔, 其他头衔, 名字个数] + 名字列表
    r = [row["头衔"], row["其他头衔"], row["名字个数"]] + row["名字"]

    r += [""]*(max_len-len(row["名字"]))

    table_data.append(r)

# 定义列名
columns = ["头衔", "其他头衔", "名字个数"] + [f"名字{i+1}" for i in range(max_len)]

table_df = pd.DataFrame(table_data,columns=columns)


# -----------------------------
# 节点颜色
# -----------------------------
def name_color(name):
    h = int(hashlib.md5(name.encode()).hexdigest()[:6],16)%360
    return f"hsl({h},70%,60%)"

# ----------------------------
# 构建图数据（节点、边）
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

# 头衔之间的边（基于匹配组）
title_edges = set()  # 用于去重，存储 (title1, title2) 排序后的元组
for group in title_groups:
    # 组内每对头衔之间加边
    for i in range(len(group)):
        for j in range(i+1, len(group)):
            t1 = group[i]
            t2 = group[j]
            # 确保头衔存在于图中（可能不在当前数据中，但以防万一）
            if t1 in title_set and t2 in title_set:
                key = tuple(sorted([t1, t2]))
                if key not in title_edges:
                    title_edges.add(key)
                    edges.append({
                        "source": f"title_{t1}",
                        "target": f"title_{t2}",
                        "lineStyle": {
                            "color": "#ffaa66",
                            "width": 2,
                            "type": "dashed"   # 可选，便于区分
                        }
                    })

# -----------------------------
# 页面布局
# -----------------------------
col1,col2=st.columns([1,2])

# 左侧表格
with col1:
    st.subheader("📋 头衔列表")
    
    # 将 DataFrame 转为 HTML 表格（不包含索引）
    html_table = table_df.to_html(index=False, border=0, escape=False)
    
    # 嵌入搜索词，转义单引号防止 JavaScript 语法错误
    search_term = search_name.replace("'", "\\'") if search_name else ""
    
    html_code = f"""
    <style>
    .table-container {{
        overflow: auto;
        height: 650px;
        border: 1px solid #e6e6e6;
        border-radius: 6px;
        position: relative;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 13px;
    }}
    th, td {{
        padding: 6px 10px;
        border-bottom: 1px solid #eee;
        white-space: nowrap;
        text-align: left;
    }}
    th {{
        background: #f6f7fb;
        position: sticky;
        top: 0;
        z-index: 3;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    }}
    th:first-child,
    td:first-child {{
        position: sticky;
        left: 0;
        background: #f6f7fb;
        z-index: 4;
        font-weight: 600;
        box-shadow: 3px 0 6px rgba(0,0,0,0.08);
    }}
    th:first-child {{
        z-index: 5;
    }}
    tr:hover td {{
        background: #f7f9fc;
    }}
    /* 高亮样式 */
    .highlight-row {{
        background-color: #ffff99 !important;
    }}
    </style>
    
    <div class="table-container" id="table-container">
    {html_table}
    </div>
    
    <script>
    (function() {{
        var searchTerm = "{search_term}".toLowerCase();
        var container = document.getElementById("table-container");
        var table = container.querySelector("table");
        if (!table) return;
        
        var rows = table.querySelectorAll("tbody tr");
        var firstMatchRow = null;
        
        // 清除之前的高亮
        rows.forEach(row => {{
            row.classList.remove("highlight-row");
        }});
        
        if (searchTerm !== "") {{
            // 遍历每一行
            for (var i = 0; i < rows.length; i++) {{
                var row = rows[i];
                var cells = row.cells;
                // 检查头衔列（第一列，索引0）
                var matched = cells[0] && cells[0].innerText.toLowerCase().includes(searchTerm);
                // 如果头衔列未匹配，再检查所有名字列（从第四列，索引3开始）
                if (!matched) {{
                    for (var j = 3; j < cells.length; j++) {{
                        if (cells[j].innerText.toLowerCase().includes(searchTerm)) {{
                            matched = true;
                            break;
                        }}
                    }}
                }}
                if (matched) {{
                    row.classList.add("highlight-row");
                    if (!firstMatchRow) {{
                        firstMatchRow = row;
                    }}
                }}
            }}
            
            // 滚动到第一个匹配行
            if (firstMatchRow) {{
                var containerRect = container.getBoundingClientRect();
                var rowRect = firstMatchRow.getBoundingClientRect();
                var scrollTop = container.scrollTop;
                var offset = rowRect.top - containerRect.top + scrollTop - 100;  // 偏移避免紧贴顶部
                container.scrollTo({{
                    top: offset,
                    behavior: "smooth"
                }});
            }}
        }}
    }})();
    </script>
    """
    
    components.html(html_code, height=680, scrolling=True)


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
    <script src="https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
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