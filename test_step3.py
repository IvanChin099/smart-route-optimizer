import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Step 3 Test - PGN Import & Export",
    page_icon="♟️",
    layout="wide",
)

st.title("♟️ Step 3 测试：PGN 序列化协议 (Import & Export)")
st.caption("实现配送任务的纯文本一键导出与还原导入。")

# 1. 序列化 (DataFrame & 参数 ➔ PGN 文本)
def export_to_pgn(depot, drivers, service_time, lang, df):
    lines = [
        f'[Depot "{depot}"]',
        f'[Drivers "{drivers}"]',
        f'[ServiceTime "{service_time}"]',
        f'[Language "{lang}"]',
        "",  # 空行分隔标头与数据
    ]

    for auto_seq, (idx, row) in enumerate(df.iterrows(), start=1):
        name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
        exact = str(row["Exact Address"]).strip() if pd.notna(row["Exact Address"]) else ""
        target_time = str(row["Target Time"]).strip() if pd.notna(row["Target Time"]) else ""
        phone = str(row["Phone"]).strip() if pd.notna(row["Phone"]) else ""
        note = str(row["Recipient / Note"]).strip() if pd.notna(row["Recipient / Note"]) else ""

        line = f'{auto_seq}. "{name}" | "{exact}" | "{target_time}" | "{phone}" | "{note}"'
        lines.append(line)

    return "\n".join(lines)


# 2. 反序列化 (PGN 文本 ➔ DataFrame & 参数)
def import_from_pgn(pgn_text):
    headers = {
        "Depot": "Kuching Waterfront, Sarawak, Malaysia",
        "Drivers": 3,
        "ServiceTime": 5,
        "Language": "English",
    }
    rows = []

    lines = pgn_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 解析标头 [Key "Value"]
        header_match = re.match(r'^\[(\w+)\s+"([^"]*)"\]$', line)
        if header_match:
            k, v = header_match.groups()
            if k in ["Drivers", "ServiceTime"]:
                headers[k] = int(v) if v.isdigit() else 3
            else:
                headers[k] = v
            continue

        # 解析数据行: 1. "Name" | "Address" | "Time" | "Phone" | "Note"
        data_match = re.match(r'^\d+\.\s+"([^"]*)"\s*\|\s*"([^"]*)"\s*\|\s*"([^"]*)"\s*\|\s*"([^"]*)"\s*\|\s*"([^"]*)"$', line)
        if data_match:
            name, exact, target_time, phone, note = data_match.groups()
            rows.append({
                "Name": name,
                "Exact Address": exact,
                "Target Time": target_time,
                "Phone": phone,
                "Recipient / Note": note,
            })

    return headers, pd.DataFrame(rows)


# 初始化 Session State 数据
if "table_data" not in st.session_state:
    st.session_state.table_data = pd.DataFrame([
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
            "Exact Address": "",
            "Target Time": "16:30",
            "Phone": "082-123456",
            "Recipient / Note": "前台签收",
        },
    ])

if "pgn_code" not in st.session_state:
    st.session_state.pgn_code = export_to_pgn(
        "Kuching Waterfront, Sarawak, Malaysia", 3, 5, "English", st.session_state.table_data
    )

# ---------------------------------------------------------------------------
# UI 布局
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("1️⃣ 表格数据 (Data Editor)")
    
    # 模拟运力参数
    c1, c2, c3 = st.columns(3)
    with c1:
        depot_val = st.text_input("仓库/起点", "Kuching Waterfront, Sarawak, Malaysia")
    with c2:
        drivers_val = st.number_input("司机人数", 1, 6, 3)
    with c3:
        service_val = st.number_input("卸货时间(分)", 1, 30, 5)

    edited_df = st.data_editor(
        st.session_state.table_data,
        num_rows="dynamic",
        use_container_width=True,
        key="data_editor_step3"
    )

    if st.button("📤 生成/更新 PGN 文本", type="primary", use_container_width=True):
        st.session_state.table_data = edited_df
        st.session_state.pgn_code = export_to_pgn(depot_val, drivers_val, service_val, "English", edited_df)
        st.success("✅ 已生成最新 PGN 序列化文本！")

with col_right:
    st.subheader("2️⃣ PGN 文本导出 & 导入区域")
    st.caption("拷贝此段文本即可保存备份，或者粘入下方进行还原：")

    pgn_input = st.text_area("PGN Data Protocol", value=st.session_state.pgn_code, height=260)

    if st.button("📥 从 PGN 文本还原导入表格", use_container_width=True):
        try:
            parsed_headers, parsed_df = import_from_pgn(pgn_input)
            st.session_state.table_data = parsed_df
            st.success("🎉 PGN 解析成功！表格与参数已同步还原！")
            st.rerun()
        except Exception as e:
            st.error(f"❌ PGN 解析失败，请检查格式是否正确: {e}")