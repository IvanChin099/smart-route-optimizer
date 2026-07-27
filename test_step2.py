import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Step 2 Test - Fallback & Exception Intercept",
    page_icon="🛠️",
    layout="wide",
)

LOCATIONIQ_TOKEN = "pk.e792503785b6b6cebd3c6c52b40b8d45"


# LocationIQ 单点测试解析
def geocode_single(query_str):
    if not query_str:
        return None
    url = f"https://us1.locationiq.com/v1/search?key={LOCATIONIQ_TOKEN}&q={urllib.parse.quote(query_str)}&format=json&countrycodes=my"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return [float(data[0]["lon"]), float(data[0]["lat"])]
    except Exception:
        pass
    return None


st.title("🛠️ Step 2 测试：无法侦测地址的“拦截修补与跳过”流程")
st.caption("真实模拟 LocationIQ 解析失败时的交互拦截界面。")

# 1. 初始化包含“正常地点”和“故意找不出的坏地点”的数据
if "table_data" not in st.session_state:
    st.session_state.table_data = pd.DataFrame(
        [
            {
                "Name": "Farley Kuching",
                "Exact Address": "1.5278, 110.3708",
                "Target Time": "14:00",
                "Phone": "012-8889999",
                "Recipient / Note": "找明哥",
            },
            {
                "Name": "Vivacity Megamall",
                "Exact Address": "",  # 使用 Name 解析 (可通)
                "Target Time": "",
                "Phone": "",
                "Recipient / Note": "",
            },
            {
                "Name": "CCK Local CityONE XYZ 999",  # 故意写错，肯定找不到
                "Exact Address": "",
                "Target Time": "15:00",
                "Phone": "019-1234567",
                "Recipient / Note": "需要补全",
            },
            {
                "Name": "Fake Supermarket ABC 888",  # 故意写错，供测试跳过
                "Exact Address": "",
                "Target Time": "",
                "Phone": "",
                "Recipient / Note": "",
            },
        ]
    )

if "unresolved_list" not in st.session_state:
    st.session_state.unresolved_list = []
if "resolved_coords" not in st.session_state:
    st.session_state.resolved_coords = {}
if "step2_stage" not in st.session_state:
    st.session_state.step2_stage = "input"  # input -> intercept -> complete

# 2. 阶段 1：表格编辑
if st.session_state.step2_stage == "input":
    st.subheader("1️⃣ 配送清单编辑")
    edited_df = st.data_editor(
        st.session_state.table_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn(
                "地点命名 / 称呼 *", required=True
            ),
            "Exact Address": st.column_config.TextColumn(
                "精确地址 / 坐标 (优先)"
            ),
            "Target Time": st.column_config.TextColumn("预约时间 (选填)"),
            "Phone": st.column_config.TextColumn("联系电话 (选填)"),
            "Recipient / Note": st.column_config.TextColumn(
                "签收人 / 备注 (选填)"
            ),
        },
    )

    if st.button("🚀 开始解析并检测地址", type="primary"):
        st.session_state.table_data = edited_df
        unresolved = []
        resolved = {}

        progress_bar = st.progress(0)
        status_text = st.empty()
        total_rows = len(edited_df)

        for idx, row in edited_df.iterrows():
            name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
            exact = (
                str(row["Exact Address"]).strip()
                if pd.notna(row["Exact Address"])
                else ""
            )

            status_text.text(f"⚡ 正在检测第 {idx+1}/{total_rows} 个地点: {name}")
            progress_bar.progress((idx + 1) / total_rows)

            # 优先级 1: Exact Address -> 优先级 2: Name
            query_used = exact if exact else name
            c = geocode_single(query_used)

            if c:
                resolved[idx] = {
                    "Name": name,
                    "Coords": c,
                    "QueryUsed": query_used,
                }
            else:
                unresolved.append(
                    {
                        "row_id": idx,
                        "Name": name,
                        "Exact Address": exact,
                        "Target Time": row.get("Target Time", ""),
                        "Phone": row.get("Phone", ""),
                        "Recipient / Note": row.get("Recipient / Note", ""),
                    }
                )
            time.sleep(0.3)

        status_text.empty()
        progress_bar.empty()

        st.session_state.resolved_coords = resolved
        st.session_state.unresolved_list = unresolved

        if unresolved:
            st.session_state.step2_stage = "intercept"
            st.rerun()
        else:
            st.session_state.step2_stage = "complete"
            st.rerun()

# 3. 阶段 2：拦截修补面板 (Intercept Panel)
elif st.session_state.step2_stage == "intercept":
    st.error("⚠️ 检测到有地点无法通过 LocationIQ 自动定位！请进行补全或选择跳过：")

    unresolved = st.session_state.unresolved_list
    skip_indices = []
    updates = {}

    with st.form("fix_form"):
        for item in unresolved:
            rid = item["row_id"]
            st.markdown(f"### 📍 无法识别的地点：`{item['Name']}`")

            col1, col2 = st.columns([3, 1])
            with col1:
                new_addr = st.text_input(
                    f"请在此为【{item['Name']}】补充 Google Maps 精确地址或坐标：",
                    value=item["Exact Address"],
                    key=f"input_{rid}",
                    placeholder="例: 1.5585, 110.3441 或 Plaza Merdeka, Kuching",
                )
                updates[rid] = new_addr
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                should_skip = st.checkbox("🗑️ 跳过此地点", key=f"skip_{rid}")
                if should_skip:
                    skip_indices.append(rid)

            st.divider()

        btn_apply = st.form_submit_button(
            "🔄 应用修改并重新验证", type="primary"
        )

    if btn_apply:
        # 处理更新与跳过
        for item in unresolved:
            rid = item["row_id"]
            if rid in skip_indices:
                continue  # 用户选择跳过

            new_val = updates.get(rid, "").strip()
            if new_val:
                c = geocode_single(new_val)
                if c:
                    st.session_state.resolved_coords[rid] = {
                        "Name": item["Name"],
                        "Coords": c,
                        "QueryUsed": new_val,
                    }
                    # 同步回 session DataFrame
                    st.session_state.table_data.at[rid, "Exact Address"] = (
                        new_val
                    )

        # 重新整理未解决列表
        st.session_state.unresolved_list = [
            item
            for item in unresolved
            if item["row_id"]
            not in st.session_state.resolved_coords
            and item["row_id"] not in skip_indices
        ]

        if not st.session_state.unresolved_list:
            st.session_state.step2_stage = "complete"
            st.success("🎉 所有异常地点处理完毕！")
            st.rerun()
        else:
            st.warning("⚠️ 仍有部分补充的地址无法解析，请检查后再次提交。")

# 4. 阶段 3：成功通过，输出最终有效站点列表
elif st.session_state.step2_stage == "complete":
    st.balloons()
    st.success("✅ 站点解析与校验 100% 完成！准备进入路线规划算法：")

    final_data = []
    for rid, data in st.session_state.resolved_coords.items():
        original_row = st.session_state.table_data.loc[rid]
        final_data.append(
            {
                "序号": len(final_data) + 1,
                "地点名称": data["Name"],
                "使用的定位串": data["QueryUsed"],
                "经纬度坐标": data["Coords"],
                "预约时间": original_row["Target Time"],
                "电话": original_row["Phone"],
                "备注": original_row["Recipient / Note"],
            }
        )

    st.dataframe(pd.DataFrame(final_data), use_container_width=True)

    if st.button("🔄 重新测试/重置"):
        st.session_state.step2_stage = "input"
        st.rerun()