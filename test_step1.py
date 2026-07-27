import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Step 1 Test - Table Optimization",
    page_icon="📋",
    layout="wide",
)

# 注入 CSS：强制隐藏 Streamlit 表格原生的 Download CSV 图标，并保持放大与工具栏常驻
st.markdown(
    """
    <style>
    /* 1. 隐藏 Streamlit 原生的下载 CSV 按钮 (data-testid="stElementToolbar") */
    button[title="Download data as a CSV"] {
        display: none !important;
    }

    /* 2. 让表格右上角其余工具栏（放大/删行）保持可见 */
    div[data-testid="stElementToolbar"] {
        opacity: 1 !important;
        visibility: visible !important;
        display: flex !important;
        background-color: #f0f2f6 !important;
        padding: 4px 8px !important;
        border-radius: 6px !important;
        border: 1px solid #d1d5db !important;
    }
    
    /* 放大工具栏图标 */
    div[data-testid="stElementToolbar"] button {
        transform: scale(1.25) !important;
        margin: 0 4px !important;
    }

    /* 操作提示栏样式 */
    .toolbar-tip {
        background-color: #eef2ff;
        border-left: 4px solid #4f46e5;
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #3730a3 !important;
        font-weight: 500;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("📋 Step 1 测试：结构化配送清单与双重定位")
st.caption("优先使用 Exact Address，未填则自动回退至 Name，可选字段允许留空。")

# 1. 初始化预设数据 (不含序号列)
if "table_data" not in st.session_state:
    st.session_state.table_data = pd.DataFrame(
        [
            {
                "Name": "Farley Kuching",
                "Exact Address": "1.5278, 110.3708",
                "Target Time": "14:00",
                "Phone": "012-8889999",
                "Recipient / Note": "找明哥 / 卸在后门",
            },
            {
                "Name": "Vivacity Megamall",
                "Exact Address": "Vivacity Megamall, Jalan Wan Alwi, Kuching",
                "Target Time": "",
                "Phone": "",
                "Recipient / Note": "",
            },
            {
                "Name": "The Spring Shopping Mall",
                "Exact Address": "",  # 留空，测试自动回退使用 Name
                "Target Time": "16:30",
                "Phone": "082-123456",
                "Recipient / Note": "前台签收",
            },
            {
                "Name": "Unknown Place ABC",
                "Exact Address": "",  # 供后续 Step 2 测试
                "Target Time": "",
                "Phone": "",
                "Recipient / Note": "",
            },
        ]
    )

st.subheader("1️⃣ 配送清单编辑表 (Data Editor)")

# 提示栏
st.markdown(
    """
    <div class="toolbar-tip">
        🛠️ <b>表格右上角功能说明：</b>
        🔍 <b>[放大图标]</b> 全屏编辑表格 &nbsp;|&nbsp; 
        🗑️ <b>[垃圾桶图标]</b> 删除选中行 &nbsp;|&nbsp; 
        ➕ <b>[表格底部 +]</b> 新增行
    </div>
    """,
    unsafe_allow_html=True,
)

# 2. 渲染交互式表格 (隐藏了自带的 CSV 下载按钮)
edited_df = st.data_editor(
    st.session_state.table_data,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Name": st.column_config.TextColumn("地点命名 / 称呼 *", required=True),
        "Exact Address": st.column_config.TextColumn("精确地址 / 坐标 (优先)"),
        "Target Time": st.column_config.TextColumn("预约时间 (选填)"),
        "Phone": st.column_config.TextColumn("联系电话 (选填)"),
        "Recipient / Note": st.column_config.TextColumn("签收人 / 备注 (选填)"),
    },
)

st.divider()

# 3. 提取与解析测试
if st.button("🚀 提取并测试解析优先级", type="primary"):
    st.subheader("2️⃣ 解析结果汇总 (Resolution Output)")

    resolved_list = []

    for auto_seq, (idx, row) in enumerate(edited_df.iterrows(), start=1):
        name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
        exact_addr = (
            str(row["Exact Address"]).strip()
            if pd.notna(row["Exact Address"])
            else ""
        )
        target_time = (
            str(row["Target Time"]).strip()
            if pd.notna(row["Target Time"])
            else ""
        )
        phone = str(row["Phone"]).strip() if pd.notna(row["Phone"]) else ""
        note = (
            str(row["Recipient / Note"]).strip()
            if pd.notna(row["Recipient / Note"])
            else ""
        )

        # 双重定位优先级判断
        if exact_addr:
            query_used = exact_addr
            strategy = "🟢 使用精确地址 (Exact Address)"
        elif name:
            query_used = name
            strategy = "🟡 降级使用地点命名 (Fallback to Name)"
        else:
            query_used = "N/A"
            strategy = "🔴 两个字段均未填"

        resolved_list.append(
            {
                "序号": auto_seq,
                "地点名称": name,
                "实际用于定位的字符串": query_used,
                "定位策略": strategy,
                "预约时间": target_time if target_time else "无",
                "电话": phone if phone else "无",
                "备注": note if note else "无",
            }
        )

    res_df = pd.DataFrame(resolved_list)
    st.dataframe(res_df, use_container_width=True)