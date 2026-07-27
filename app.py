import math
import re
import time
import urllib.parse
import folium
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# 1. 页面基本配置与 CSS 样式
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Route AI - Intelligent Fleet Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCATIONIQ_TOKEN = "pk.e792503785b6b6cebd3c6c52b40b8d45"

st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa !important; }
    p, span, label, div { color: #1f2937 !important; }
    
    .main-header {
        font-size: 1.8rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF8F00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .mobile-card {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #1f2937 !important;
    }
    
    /* 隐藏原生表格的 CSV 下载按钮 */
    button[title="Download data as a CSV"] {
        display: none !important;
    }

    /* 放大表格右上角工具栏并保持常驻 */
    div[data-testid="stElementToolbar"] {
        opacity: 1 !important;
        visibility: visible !important;
        display: flex !important;
        background-color: #f0f2f6 !important;
        padding: 4px 8px !important;
        border-radius: 6px !important;
        border: 1px solid #d1d5db !important;
    }
    div[data-testid="stElementToolbar"] button {
        transform: scale(1.2) !important;
        margin: 0 3px !important;
    }
    .toolbar-tip {
        background-color: #eef2ff;
        border-left: 4px solid #4f46e5;
        padding: 8px 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        color: #3730a3 !important;
        font-weight: 500;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 2. 4 语言字典配置 (100% 全覆盖无漏网之鱼)
# ---------------------------------------------------------------------------
LANGUAGES = {
    "English": {
        "title": "🚚 Smart Route AI System",
        "subtitle": "Commercial AI Fleet Optimizer | Multi-Driver Round Trip Support",
        "sidebar_title": "🚚 Control Center",
        "sidebar_caption": "Commercial Fleet Optimization Platform",
        "depot_label": "🏭 Depot / Starting Point:",
        "fleet_header": "🚚 Capacity Settings",
        "drivers_count": "Number of Drivers",
        "service_time": "Unloading Time (mins)",
        "btn_submit": "⚡ Check Addresses & Validate List",
        "rules_title": "ℹ️ System Rules & Limits",
        "rules_body": """
        * 📍 **Max Destinations**: Up to **30 locations**.
        * 👥 **Max Drivers**: Supports **1 ~ 6 drivers**.
        * ⏱️ **Max Shift Time**: **6 Hours** per driver limit.
        * 🔄 **Round-Trip**: Includes time to return to depot.
        """,
        "section_input_title": "📋 1️⃣ Delivery List & PGN Import/Export",
        "toolbar_tip": "🛠️ <b>Table Toolbar Tips:</b> 🔍 <b>[Full Screen]</b> Edit &nbsp;|&nbsp; 🗑️ <b>[Trash]</b> Delete Row &nbsp;|&nbsp; ➕ <b>[Bottom +]</b> Add Row &nbsp;|&nbsp; Exact Address prioritized over Name.",
        "col_name": "Location Name / Label *",
        "col_exact": "Exact Address / Coords (Priority)",
        "col_time": "Target Time (Optional)",
        "col_phone": "Phone (Optional)",
        "col_note": "Recipient / Note (Optional)",
        "pgn_expander": "♟️ PGN Protocol (Text Import & One-Click Backup)",
        "btn_pgn_import": "📥 Restore / Import from PGN",
        "progress_parsing": "⚡ Parsing {seq}/{total}: {name}",
        "err_limit_stops": "⚠️ You entered {count} stops, which exceeds the maximum limit of 30! Please reduce locations.",
        "err_no_solution": "❌ Algorithm could not find a feasible solution. Try adding more drivers!",
        "confirm_title": "✅ All Addresses Verified & Confirmed! Please Review List:",
        "tbl_seq": "No.",
        "tbl_name": "Location Name",
        "tbl_query": "Address/Coords Used",
        "tbl_latlng": "Coordinates",
        "tbl_time": "Target Time",
        "tbl_phone": "Phone Number",
        "tbl_note": "Recipient / Note",
        "val_none": "None",
        "kpi_stops": "📦 Total Stops",
        "kpi_drivers": "🚚 Active Drivers",
        "kpi_max_time": "⏱️ Max Shift Time (Inc. Return)",
        "kpi_total_time": "📊 Total Cumulative Time",
        "map_title": "🗺️ Live Route Overview (Round Trip)",
        "list_title": "📱 Driver Dispatch & Navigation",
        "driver_label": "🚚 Driver {id}",
        "driver_est_time": "Est. Shift Time: {time} mins (Inc. Return)",
        "stop_label": "Stop {id}",
        "return_label": "🏁 Final Stop (Return to Depot)",
        "btn_gmaps": "🗺️ Google Maps",
        "btn_waze": "🚙 Waze Nav",
        "btn_gmaps_return": "🗺️ Return Google Maps",
        "btn_waze_return": "🚙 Return Waze Nav",
        "btn_reset": "🔄 Modify Parameters / Reset Task",
        "btn_back": "↩️ Return to Edit",
        "btn_confirm_continue": "🚀 Confirm & Generate Optimal Routes",
        "units_stops": "stops",
        "units_drivers": "drivers",
        "units_mins": "mins",
    },
    "中文": {
        "title": "🚚 Smart Route AI 智能调度系统",
        "subtitle": "商业级 API 驱动 | 支持双重定位与 PGN 协议",
        "sidebar_title": "🚚 调度控制中心",
        "sidebar_caption": "商业级多司机排单算法平台",
        "depot_label": "🏭 发货起点 (仓库/餐厅):",
        "fleet_header": "🚚 运力参数设置",
        "drivers_count": "司机人数",
        "service_time": "卸货耗时(分)",
        "btn_submit": "⚡ 校验地址并开始检测",
        "rules_title": "ℹ️ 系统规则与参数上限说明",
        "rules_body": """
        * 📍 **最多送货点**：上限 **30 个地点**。
        * 👥 **最多司机数**：支持 **1 ~ 6 位司机**。
        * ⏱️ **单人最长工时**：每位司机上限 **6 小时**（含返程）。
        * 🔄 **闭环返程计算**：已强制包含司机返回仓库的时间。
        """,
        "section_input_title": "📋 1️⃣ 配送清单与 PGN 导入导出",
        "toolbar_tip": "🛠️ <b>表格工具栏提示：</b> 🔍 <b>[放大]</b> 全屏编辑 &nbsp;|&nbsp; 🗑️ <b>[垃圾桶]</b> 删除行 &nbsp;|&nbsp; ➕ <b>[表格底部 +]</b> 新增行 &nbsp;|&nbsp; 优先使用 Exact Address，未填则自动回退至 Name。",
        "col_name": "地点命名 / 称呼 *",
        "col_exact": "精确地址 / 坐标 (优先)",
        "col_time": "预约时间 (选填)",
        "col_phone": "联系电话 (选填)",
        "col_note": "签收人 / 备注 (选填)",
        "pgn_expander": "♟️ PGN 序列化协议 (文本导入与一键备份)",
        "btn_pgn_import": "📥 从 PGN 文本还原导入",
        "progress_parsing": "⚡ 解析中 {seq}/{total}: {name}",
        "err_limit_stops": "⚠️ 当前输入了 {count} 个送货地点，超过上限 30 个！请减少地点。",
        "err_no_solution": "❌ 运筹算法未能求解出方案，请尝试增加司机人数！",
        "confirm_title": "✅ 站点解析与校验 100% 完成！请确认清单：",
        "tbl_seq": "序号",
        "tbl_name": "地点名称",
        "tbl_query": "用于定位的地址/坐标",
        "tbl_latlng": "经纬度坐标",
        "tbl_time": "预约时间",
        "tbl_phone": "联系电话",
        "tbl_note": "备注/签收人",
        "val_none": "无",
        "kpi_stops": "📦 待送货点",
        "kpi_drivers": "🚚 出动司机",
        "kpi_max_time": "⏱️ 方案最长耗时 (含返程)",
        "kpi_total_time": "📊 累积总耗时 (含返程)",
        "map_title": "🗺️ 全局实景路线看板 (闭环路径)",
        "list_title": "📱 司机派单与导航中心",
        "driver_label": "🚚 司机 {id}",
        "driver_est_time": "全程预计耗时: {time} 分钟 (含返程)",
        "stop_label": "站 {id}",
        "return_label": "🏁 终点站 (返回仓库)",
        "btn_gmaps": "🗺️ Google Maps",
        "btn_waze": "🚙 Waze 导航",
        "btn_gmaps_return": "🗺️ 返程 Google Maps",
        "btn_waze_return": "🚙 返程 Waze 导航",
        "btn_reset": "🔄 修改参数 / 重置任务",
        "btn_back": "↩️ 返回修改",
        "btn_confirm_continue": "🚀 确认无误，一键生成最佳调度方案",
        "units_stops": "个",
        "units_drivers": "位",
        "units_mins": "分钟",
    },
    "Bahasa Melayu": {
        "title": "🚚 Sistem Smart Route AI",
        "subtitle": "Pengoptimum Laluan AI Komersial | Sokongan Perjalanan Pergi-Balik",
        "sidebar_title": "🚚 Pusat Kawalan Penghantaran",
        "sidebar_caption": "Platform Pengatur Laluan Pemandu",
        "depot_label": "🏭 Depot / Lokasi Permulaan:",
        "fleet_header": "🚚 Tetapan Kapasiti",
        "drivers_count": "Bilangan Pemandu",
        "service_time": "Masa Memunggah (min)",
        "btn_submit": "⚡ Semak Alamat & Semak Senarai",
        "rules_title": "ℹ️ Peraturan & Had Sistem",
        "rules_body": """
        * 📍 **Maksimum Lokasi**: Hingga **30 lokasi**.
        * 👥 **Maksimum Pemandu**: Menyokong **1 ~ 6 pemandu**.
        * ⏱️ **Masa Kerja Maksimum**: **6 Jam** setiap pemandu.
        * 🔄 **Perjalanan Balik**: Termasuk masa kembali ke depot.
        """,
        "section_input_title": "📋 1️⃣ Senarai Penghantaran & Import/Eksport PGN",
        "toolbar_tip": "🛠️ <b>Petua Alat Jadual:</b> 🔍 <b>[Skrin Penuh]</b> Edit &nbsp;|&nbsp; 🗑️ <b>[Tong Sampah]</b> Padam Baris &nbsp;|&nbsp; ➕ <b>[Bawah +]</b> Tambah Baris &nbsp;|&nbsp; Alamat Tepat diutamakan daripada Nama.",
        "col_name": "Nama Lokasi / Label *",
        "col_exact": "Alamat Tepat / Koordinat (Keutamaan)",
        "col_time": "Masa Sasaran (Pilihan)",
        "col_phone": "Nombor Telefon (Pilihan)",
        "col_note": "Penerima / Nota (Pilihan)",
        "pgn_expander": "♟️ Protokol PGN (Import Teks & Sandaran Satu Klik)",
        "btn_pgn_import": "📥 Pulihkan / Import daripada PGN",
        "progress_parsing": "⚡ Memeriksa {seq}/{total}: {name}",
        "err_limit_stops": "⚠️ Anda memasukkan {count} lokasi, melebihi had 30! Sila kurangkan.",
        "err_no_solution": "❌ Algoritma tidak menemui penyelesaian. Sila tambah pemandu!",
        "confirm_title": "✅ Semua Alamat Disahkan! Sila Semak Senarai:",
        "tbl_seq": "No.",
        "tbl_name": "Nama Lokasi",
        "tbl_query": "Alamat/Koordinat Digunakan",
        "tbl_latlng": "Koordinat GPS",
        "tbl_time": "Masa Sasaran",
        "tbl_phone": "Nombor Telefon",
        "tbl_note": "Nota / Penerima",
        "val_none": "Tiada",
        "kpi_stops": "📦 Jumlah Lokasi",
        "kpi_drivers": "🚚 Pemandu Aktif",
        "kpi_max_time": "⏱️ Masa Terpanjang (Termasuk Balik)",
        "kpi_total_time": "📊 Jumlah Masa Pengumpulan",
        "map_title": "🗺️ Pandangan Laluan Keseluruhan",
        "list_title": "📱 Pusat Navigasi Pemandu",
        "driver_label": "🚚 Pemandu {id}",
        "driver_est_time": "Anggaran Masa: {time} minit (Termasuk Balik)",
        "stop_label": "Hentian {id}",
        "return_label": "🏁 Hentian Akhir (Kembali ke Depot)",
        "btn_gmaps": "🗺️ Google Maps",
        "btn_waze": "🚙 Waze Nav",
        "btn_gmaps_return": "🗺️ Google Maps Balik",
        "btn_waze_return": "🚙 Waze Nav Balik",
        "btn_reset": "🔄 Ubah Tetapan / Set Semula",
        "btn_back": "↩️ Kembali Edit",
        "btn_confirm_continue": "🚀 Sahkan & Hasilkan Laluan Optimal",
        "units_stops": "lokasi",
        "units_drivers": "pemandu",
        "units_mins": "minit",
    },
    "Bahasa Sarawak": {
        "title": "🚚 Sistem Smart Route AI Sarawak",
        "subtitle": "Sistem Susun Jalan Pok Driver Penghantaran | Pusing Balik Gudang",
        "sidebar_title": "🚚 Kawalan Penghantaran",
        "sidebar_caption": "Sistem Susun Jalan Driver Kuching",
        "depot_label": "🏭 Gudang / Tempat Mula:",
        "fleet_header": "🚚 Tetapan Driver",
        "drivers_count": "Jumlah Driver",
        "service_time": "Masa Punggah Barang (minit)",
        "btn_submit": "⚡ Semak Alamat Dulu",
        "rules_title": "ℹ️ Syarat & Had Sistem",
        "rules_body": """
        * 📍 **Paling Banyak Lokasi**: Sampai **30 tempat** ajak.
        * 👥 **Paling Banyak Driver**: Boleh **1 ~ 6 orang driver**.
        * ⏱️ **Masa Kerja Driver**: Paling lapan **6 Jam** sorang (sekali balek gudang).
        * 🔄 **Kira Masa Balek**: Sudah kira sekali masa driver balek ke gudang.
        """,
        "section_input_title": "📋 1️⃣ Senarai Barang & Import/Eksport PGN",
        "toolbar_tip": "🛠️ <b>Petua Alat Jadual:</b> 🔍 <b>[Besarkan]</b> Edit &nbsp;|&nbsp; 🗑️ <b>[Tong Sampah]</b> Buang Baris &nbsp;|&nbsp; ➕ <b>[Bawah +]</b> Tambah Tempat &nbsp;|&nbsp; Alamat Tepat diutamakan dulu.",
        "col_name": "Nama Tempat / Panggilan *",
        "col_exact": "Alamat Ngam / GPS (Utama)",
        "col_time": "Masa Janji (Mahu isi boleh)",
        "col_phone": "Nombor Telefon (Mahu isi boleh)",
        "col_note": "Siape Ambil / Nota (Mahu isi boleh)",
        "pgn_expander": "♟️ Protokol PGN (Simpan & Tampal Teks)",
        "btn_pgn_import": "📥 Masokkan Teks PGN Balek",
        "progress_parsing": "⚡ Tengok Tempat {seq}/{total}: {name}",
        "err_limit_stops": "⚠️ Aie, kita masok {count} tempat, dah lebih had 30! Tolong kurangkan.",
        "err_no_solution": "❌ Sik dapat carik jalan ngam lah! Cuba tambah driver agik.",
        "confirm_title": "✅ Semua Tempat Dah Ngam! Sila Tengok Senarai:",
        "tbl_seq": "No.",
        "tbl_name": "Nama Tempat",
        "tbl_query": "Alamat/GPS Guna",
        "tbl_latlng": "Lokasi GPS",
        "tbl_time": "Masa Janji",
        "tbl_phone": "Nombor Telefon",
        "tbl_note": "Nota / Siape Ambil",
        "val_none": "Sikda",
        "kpi_stops": "📦 Tempat Hantar",
        "kpi_drivers": "🚚 Driver Jalan",
        "kpi_max_time": "⏱️ Masa Paling Lapan (Sekali Balek)",
        "kpi_total_time": "📊 Jumlah Masa Semua Driver",
        "map_title": "🗺️ Peta Jalan Kamek Orang (Pusing Balek)",
        "list_title": "📱 Pusat GPS & Navigasi Driver",
        "driver_label": "🚚 Driver {id}",
        "driver_est_time": "Masa Anggaran: {time} minit (Sekali balek gudang)",
        "stop_label": "Check-in {id}",
        "return_label": "🏁 Tempat Akhir (Balek Gudang)",
        "btn_gmaps": "🗺️ Google Maps",
        "btn_waze": "🚙 Waze Nav",
        "btn_gmaps_return": "🗺️ Google Maps Balik",
        "btn_waze_return": "🚙 Waze Nav Balik",
        "btn_reset": "🔄 Tukar Tetapan / Mula Balek",
        "btn_back": "↩️ Balek Edit",
        "btn_confirm_continue": "🚀 Ngam Dah, Susun Jalan Paling Pantas",
        "units_stops": "biji",
        "units_drivers": "orang",
        "units_mins": "minit",
    },
}

# ---------------------------------------------------------------------------
# 3. PGN 序列化与反序列化函数
# ---------------------------------------------------------------------------
def export_to_pgn(depot, drivers, service_time, lang, df):
    lines = [
        f'[Depot "{depot}"]',
        f'[Drivers "{drivers}"]',
        f'[ServiceTime "{service_time}"]',
        f'[Language "{lang}"]',
        "",
    ]
    for auto_seq, (idx, row) in enumerate(df.iterrows(), start=1):
        name = str(row["Name"]).strip() if pd.notna(row["Name"]) and str(row["Name"]).strip() != "None" else ""
        exact = str(row["Exact Address"]).strip() if pd.notna(row["Exact Address"]) and str(row["Exact Address"]).strip() != "None" else ""
        target_time = str(row["Target Time"]).strip() if pd.notna(row["Target Time"]) and str(row["Target Time"]).strip() != "None" else ""
        phone = str(row["Phone"]).strip() if pd.notna(row["Phone"]) and str(row["Phone"]).strip() != "None" else ""
        note = str(row["Recipient / Note"]).strip() if pd.notna(row["Recipient / Note"]) and str(row["Recipient / Note"]).strip() != "None" else ""
        
        if name or exact:
            lines.append(f'{auto_seq}. "{name}" | "{exact}" | "{target_time}" | "{phone}" | "{note}"')
    return "\n".join(lines)


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
        header_match = re.match(r'^\[(\w+)\s+"([^"]*)"\]$', line)
        if header_match:
            k, v = header_match.groups()
            if k in ["Drivers", "ServiceTime"]:
                headers[k] = int(v) if v.isdigit() else 3
            else:
                headers[k] = v
            continue

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


# ---------------------------------------------------------------------------
# 4. 算法与地理解析函数
# ---------------------------------------------------------------------------
def geocode_single(query_str):
    if not query_str or len(query_str.strip()) < 3:
        return None
    url = f"https://us1.locationiq.com/v1/search?key={LOCATIONIQ_TOKEN}&q={urllib.parse.quote(query_str)}&format=json&countrycodes=my"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                lng = float(data[0]["lon"])
                lat = float(data[0]["lat"])
                if 0.8 <= lat <= 5.0 and 109.5 <= lng <= 115.8:
                    return [lng, lat]
    except Exception:
        pass
    return None


def get_time_matrix(coords):
    num_locs = len(coords)
    matrix = [[0] * num_locs for _ in range(num_locs)]
    AVERAGE_SPEED_MPS = 9.72
    ROAD_DETOUR_FACTOR = 1.3

    for i in range(num_locs):
        for j in range(num_locs):
            if i == j:
                matrix[i][j] = 0
            else:
                lng1, lat1 = coords[i]
                lng2, lat2 = coords[j]
                rad_lat1, rad_lat2 = math.radians(lat1), math.radians(lat2)
                d_lat = math.radians(lat2 - lat1)
                d_lng = math.radians(lng2 - lng1)

                a = math.sin(d_lat / 2) ** 2 + math.cos(rad_lat1) * math.cos(rad_lat2) * math.sin(d_lng / 2) ** 2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                distance_meters = 6371000 * c
                matrix[i][j] = int((distance_meters * ROAD_DETOUR_FACTOR) / AVERAGE_SPEED_MPS)
    return matrix


def solve_vrp_multi_vehicle(time_matrix, service_times, num_vehicles):
    num_locs = len(time_matrix)
    manager = pywrapcp.RoutingIndexManager(num_locs, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return time_matrix[from_node][to_node] + service_times[to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    time_dimension_name = "Time"
    routing.AddDimension(
        transit_callback_index,
        3600,
        21600,
        True,
        time_dimension_name,
    )
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    time_dimension.SetGlobalSpanCostCoefficient(40)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_parameters)

    routes = {}
    if solution:
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(node)
                index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))

            if len(route) > 2:
                routes[vehicle_id] = route
    return routes


def build_nav_urls(dest_name, lat, lng):
    encoded_name = urllib.parse.quote(dest_name)
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&destination_place_id={encoded_name}"
    waze_url = f"https://waze.com/ul?ll={lat},{lng}&navigate=yes"
    return gmaps_url, waze_url


# ---------------------------------------------------------------------------
# 5. Session State 初始化
# ---------------------------------------------------------------------------
if "table_data" not in st.session_state:
    st.session_state.table_data = pd.DataFrame([
        {
            "Name": "Farley Kuching",
            "Exact Address": "1.5278, 110.3708",
            "Target Time": "14:00",
            "Phone": "012-8889999",
            "Recipient / Note": "Ming/ Unload at the back door",
        },
        {
            "Name": "Vivacity Megamall",
            "Exact Address": "Vivacity Megamall, Jalan Wan Alwi, Kuching",
            "Target Time": "",
            "Phone": "",
            "Recipient / Note": "Hong/ Lobby A",
        },
        {
            "Name": "The Spring Shopping Mall",
            "Exact Address": "",
            "Target Time": "16:30",
            "Phone": "082-123456",
            "Recipient / Note": "Ah Lee/ Counter 4",
        },
    ])

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "unresolved_list" not in st.session_state:
    st.session_state.unresolved_list = []
if "resolved_coords" not in st.session_state:
    st.session_state.resolved_coords = {}
if "has_celebrated" not in st.session_state:
    st.session_state.has_celebrated = False

# ---------------------------------------------------------------------------
# 6. 侧边栏（Sidebar）
# ---------------------------------------------------------------------------
with st.sidebar:
    selected_lang_name = st.selectbox(
        "🌐 Language / 语言",
        ["English", "中文", "Bahasa Melayu", "Bahasa Sarawak"],
        index=0,
    )
    L = LANGUAGES[selected_lang_name]

    st.markdown(f"## {L['sidebar_title']}")
    st.caption(L["sidebar_caption"])
    st.divider()

    depot_input = st.text_input(
        L["depot_label"],
        "Kuching Waterfront, Sarawak, Malaysia",
    )

    st.subheader(L["fleet_header"])
    col_v, col_s = st.columns(2)
    with col_v:
        num_drivers = st.number_input(
            L["drivers_count"], min_value=1, max_value=6, value=3
        )
    with col_s:
        service_time_min = st.number_input(
            L["service_time"], min_value=1, max_value=30, value=5
        )

    st.divider()
    btn_submit = st.button(
        L["btn_submit"], type="primary", use_container_width=True
    )

    with st.expander(L["rules_title"]):
        st.markdown(L["rules_body"])

# ---------------------------------------------------------------------------
# 7. 主界面 UI 与流程控制
# ---------------------------------------------------------------------------
st.markdown(f'<div class="main-header">{L["title"]}</div>', unsafe_allow_html=True)
st.caption(L["subtitle"])
st.divider()

# --- 阶段 A: 输入与 PGN 转换 ---
if st.session_state.stage == "input":
    st.subheader(L["section_input_title"])

    st.markdown(
        f'<div class="toolbar-tip">{L["toolbar_tip"]}</div>',
        unsafe_allow_html=True,
    )

    edited_df = st.data_editor(
        st.session_state.table_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Name": st.column_config.TextColumn(L["col_name"], required=True),
            "Exact Address": st.column_config.TextColumn(L["col_exact"]),
            "Target Time": st.column_config.TextColumn(L["col_time"]),
            "Phone": st.column_config.TextColumn(L["col_phone"]),
            "Recipient / Note": st.column_config.TextColumn(L["col_note"]),
        },
        key="main_data_editor"
    )
    st.session_state.table_data = edited_df

    with st.expander(L["pgn_expander"]):
        pgn_current = export_to_pgn(depot_input, num_drivers, service_time_min, selected_lang_name, edited_df)
        pgn_text_area = st.text_area("PGN Protocol Data", value=pgn_current, height=180)
        
        if st.button(L["btn_pgn_import"], use_container_width=True):
            try:
                headers, parsed_df = import_from_pgn(pgn_text_area)
                st.session_state.table_data = parsed_df
                st.success("🎉 PGN Protocol Restored!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ PGN Format Error: {e}")

    if btn_submit:
        valid_rows_list = []
        for idx, row in edited_df.iterrows():
            name_val = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
            exact_val = str(row["Exact Address"]).strip() if pd.notna(row["Exact Address"]) else ""
            if name_val and name_val != "None" and name_val != "nan":
                valid_rows_list.append((name_val, exact_val, row))

        if len(valid_rows_list) > 30:
            st.error(L["err_limit_stops"].format(count=len(valid_rows_list)))
        elif len(valid_rows_list) == 0:
            st.warning("⚠️ Please fill in at least one valid location!")
        else:
            depot_coords = geocode_single(depot_input)
            if not depot_coords:
                st.error(f"❌ Unable to geocode depot: `{depot_input}`!")
            else:
                unresolved = []
                resolved = {0: {"Name": depot_input, "Coords": depot_coords, "QueryUsed": depot_input}}

                progress_bar = st.progress(0)
                status_text = st.empty()
                total_rows = len(valid_rows_list)

                for seq, (name, exact, original_row) in enumerate(valid_rows_list, start=1):
                    row_id = seq
                    # ⚡ 多语言绑定的解析进度文字
                    status_text.text(L["progress_parsing"].format(seq=seq, total=total_rows, name=name))
                    progress_bar.progress(seq / total_rows)

                    query_used = exact if exact else name
                    c = geocode_single(query_used)

                    if c:
                        resolved[row_id] = {
                            "Name": name, 
                            "Coords": c, 
                            "QueryUsed": query_used,
                            "Target Time": original_row.get("Target Time", ""),
                            "Phone": original_row.get("Phone", ""),
                            "Recipient / Note": original_row.get("Recipient / Note", ""),
                        }
                    else:
                        unresolved.append({
                            "row_id": row_id,
                            "Name": name,
                            "Exact Address": exact,
                            "Target Time": original_row.get("Target Time", ""),
                            "Phone": original_row.get("Phone", ""),
                            "Recipient / Note": original_row.get("Recipient / Note", ""),
                        })
                    time.sleep(0.2)

                status_text.empty()
                progress_bar.empty()

                st.session_state.resolved_coords = resolved
                st.session_state.unresolved_list = unresolved
                st.session_state.has_celebrated = False

                if unresolved:
                    st.session_state.stage = "intercept"
                    st.rerun()
                else:
                    st.session_state.stage = "confirm"
                    st.rerun()

# --- 阶段 B: 诊所修补拦截 (Intercept Panel) ---
elif st.session_state.stage == "intercept":
    st.error("⚠️ Some addresses could not be geocoded automatically!")

    unresolved = st.session_state.unresolved_list
    skip_indices = []
    updates = {}

    with st.form("fix_intercept_form"):
        for item in unresolved:
            rid = item["row_id"]
            st.markdown(f"### 📍 Location: `{item['Name']}`")

            col1, col2 = st.columns([3, 1])
            with col1:
                new_addr = st.text_input(
                    f"Google Maps Address for 【{item['Name']}】:",
                    value=item["Exact Address"],
                    key=f"input_{rid}",
                    placeholder="e.g. 1.5585, 110.3441 or Plaza Merdeka, Kuching",
                )
                updates[rid] = new_addr
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                should_skip = st.checkbox("🗑️ Skip Stop", key=f"skip_{rid}")
                if should_skip:
                    skip_indices.append(rid)

            st.divider()

        btn_apply = st.form_submit_button("🔄 Apply & Re-validate", type="primary")

    if btn_apply:
        for item in unresolved:
            rid = item["row_id"]
            if rid in skip_indices:
                continue

            new_val = updates.get(rid, "").strip()
            if new_val:
                c = geocode_single(new_val)
                if c:
                    st.session_state.resolved_coords[rid] = {
                        "Name": item["Name"],
                        "Coords": c,
                        "QueryUsed": new_val,
                        "Target Time": item["Target Time"],
                        "Phone": item["Phone"],
                        "Recipient / Note": item["Recipient / Note"],
                    }

        st.session_state.unresolved_list = [
            item for item in unresolved
            if item["row_id"] not in st.session_state.resolved_coords
            and item["row_id"] not in skip_indices
        ]

        if not st.session_state.unresolved_list:
            st.session_state.stage = "confirm"
            st.session_state.has_celebrated = False
            st.rerun()
        else:
            st.warning("⚠️ Some updated addresses are still unparseable.")

# --- 阶段 C: 确认页面 (Confirm Stage) ---
elif st.session_state.stage == "confirm":
    st.success(L["confirm_title"])

    resolved = st.session_state.resolved_coords
    confirm_data = []

    for seq, rid in enumerate(sorted(resolved.keys()), start=1):
        if rid == 0:
            continue
        item = resolved[rid]
        
        # ⚡ 全面绑定语言字典的表头列名与 None 值
        confirm_data.append({
            L["tbl_seq"]: seq - 1,
            L["tbl_name"]: item["Name"],
            L["tbl_query"]: item["QueryUsed"],
            L["tbl_latlng"]: f"{item['Coords'][1]:.4f}, {item['Coords'][0]:.4f}",
            L["tbl_time"]: item.get("Target Time", "") if item.get("Target Time") else L["val_none"],
            L["tbl_phone"]: item.get("Phone", "") if item.get("Phone") else L["val_none"],
            L["tbl_note"]: item.get("Recipient / Note", "") if item.get("Recipient / Note") else L["val_none"],
        })

    st.dataframe(pd.DataFrame(confirm_data), use_container_width=True, hide_index=True)

    st.divider()

    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        if st.button(L["btn_confirm_continue"], type="primary", use_container_width=True):
            st.session_state.stage = "complete"
            st.rerun()
    with col_btn2:
        if st.button(L["btn_back"], use_container_width=True):
            st.session_state.stage = "input"
            st.rerun()

# --- 阶段 D: OR-Tools 路线求解与地图渲染 ---
elif st.session_state.stage == "complete":
    resolved = st.session_state.resolved_coords
    
    valid_indices = sorted(resolved.keys())
    coords = [resolved[i]["Coords"] for i in valid_indices]
    valid_locations = [resolved[i]["Name"] for i in valid_indices]

    if len(coords) >= 2:
        service_times_sec = [0] + [service_time_min * 60] * (len(coords) - 1)
        time_matrix = get_time_matrix(coords)
        routes = solve_vrp_multi_vehicle(time_matrix, service_times_sec, num_drivers)

        if routes:
            if not st.session_state.has_celebrated:
                st.balloons()
                st.session_state.has_celebrated = True
            
            total_stops = len(coords) - 1
            active_drivers = len(routes)

            driver_times = []
            for vehicle_id, route in routes.items():
                v_sec = sum(
                    time_matrix[route[i]][route[i + 1]] + service_times_sec[route[i + 1]]
                    for i in range(len(route) - 1)
                )
                driver_times.append(v_sec)

            max_time_min = round(max(driver_times) / 60, 1) if driver_times else 0
            total_time_min = round(sum(driver_times) / 60, 1) if driver_times else 0

            r1_col1, r1_col2 = st.columns(2)
            with r1_col1:
                st.metric(L["kpi_stops"], f"{total_stops} {L['units_stops']}")
            with r1_col2:
                st.metric(L["kpi_drivers"], f"{active_drivers} {L['units_drivers']}")

            r2_col1, r2_col2 = st.columns(2)
            with r2_col1:
                st.metric(L["kpi_max_time"], f"{max_time_min} {L['units_mins']}")
            with r2_col2:
                st.metric(L["kpi_total_time"], f"{total_time_min} {L['units_mins']}")

            st.markdown("<br>", unsafe_allow_html=True)

            col_map, col_list = st.columns([1.2, 1])
            colors = ["blue", "green", "purple", "orange", "darkred", "cadetblue"]

            with col_map:
                st.subheader(L["map_title"])
                center_lat, center_lng = coords[0][1], coords[0][0]
                m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

                folium.Marker(
                    [coords[0][1], coords[0][0]],
                    popup="Depot Center",
                    tooltip=f"🏭 {valid_locations[0]}",
                    icon=folium.Icon(color="red", icon="home"),
                ).add_to(m)

                for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
                    color = colors[driver_idx % len(colors)]
                    for step_idx, node_idx in enumerate(route[1:-1], start=1):
                        lng, lat = coords[node_idx]
                        folium.Marker(
                            [lat, lng],
                            popup=f"Driver {vehicle_id + 1} - Stop {step_idx}: {valid_locations[node_idx]}",
                            tooltip=f"🚚 Driver {vehicle_id + 1} | Stop {step_idx}",
                            icon=folium.Icon(color=color, icon="info-sign"),
                        ).add_to(m)

                    path_coords = [[coords[node][1], coords[node][0]] for node in route]
                    folium.PolyLine(path_coords, color=color, weight=5, opacity=0.85).add_to(m)

                st_folium(m, width="100%", height=420, key="v25_full_system_map")

            with col_list:
                st.subheader(L["list_title"])

                for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
                    v_time_sec = sum(
                        time_matrix[route[i]][route[i + 1]] + service_times_sec[route[i + 1]]
                        for i in range(len(route) - 1)
                    )

                    driver_title = L["driver_label"].format(id=vehicle_id + 1)
                    driver_time_str = L["driver_est_time"].format(time=round(v_time_sec / 60, 1))

                    st.markdown(
                        f"""
                        <div class="mobile-card">
                            <h3 style="margin:0; color:#1f2937;">{driver_title}</h3>
                            <p style="margin:5px 0 0 0; color:#4b5563; font-weight:bold;">{driver_time_str}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    for step_idx, node_idx in enumerate(route[1:-1], start=1):
                        loc_name = valid_locations[node_idx]
                        lng, lat = coords[node_idx]
                        gmaps_url, waze_url = build_nav_urls(loc_name, lat, lng)

                        stop_title = f"{L['stop_label'].format(id=step_idx)}: {loc_name}"
                        st.markdown(f"**{stop_title}**")
                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            st.link_button(L["btn_gmaps"], gmaps_url, use_container_width=True)
                        with btn_c2:
                            st.link_button(L["btn_waze"], waze_url, use_container_width=True)
                        st.divider()

                    depot_name = valid_locations[0]
                    depot_lng, depot_lat = coords[0]
                    gmaps_depot, waze_depot = build_nav_urls(f"Return: {depot_name}", depot_lat, depot_lng)

                    return_title = f"{L['return_label']}: {depot_name}"
                    st.markdown(f"**{return_title}**")
                    btn_d1, btn_d2 = st.columns(2)
                    with btn_d1:
                        st.link_button(L["btn_gmaps_return"], gmaps_depot, use_container_width=True)
                    with btn_d2:
                        st.link_button(L["btn_waze_return"], waze_depot, use_container_width=True)
                    st.divider()

            if st.button(L["btn_reset"], use_container_width=True):
                st.session_state.stage = "input"
                st.session_state.has_celebrated = False
                st.rerun()
        else:
            st.error(L["err_no_solution"])
            if st.button(L["btn_back"]):
                st.session_state.stage = "input"
                st.session_state.has_celebrated = False
                st.rerun()