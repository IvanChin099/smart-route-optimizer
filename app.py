import math
import time
import urllib.parse
import folium
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# 1. 页面基本配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Route AI - Intelligent Dispatch System",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCATIONIQ_TOKEN = "pk.e792503785b6b6cebd3c6c52b40b8d45"

# ---------------------------------------------------------------------------
# 2. 4 语言字典配置 (默认英文, 华文, 马来文, Bahasa Sarawak)
# ---------------------------------------------------------------------------
LANGUAGES = {
    "English": {
        "title": "🚚 Smart Route AI System",
        "subtitle": "Commercial AI Fleet Optimizer | Multi-Driver Round Trip Support",
        "sidebar_title": "🚚 Dispatch Control Center",
        "sidebar_caption": "Commercial Fleet Optimization Platform",
        "lang_select": "🌐 Select Language / 选择语言",
        "depot_label": "🏭 Depot / Starting Point:",
        "stops_label": "📍 Delivery Destinations (One per line):",
        "fleet_header": "🚚 Capacity Settings",
        "drivers_count": "Number of Drivers",
        "service_time": "Unloading Time (mins)",
        "btn_submit": "⚡ Generate Optimal Routes",
        "rules_title": "ℹ️ System Rules & Limits",
        "rules_body": """
        * 📍 **Max Destinations**: Up to **30 locations**.
        * 👥 **Max Drivers**: Supports **1 ~ 6 drivers**.
        * ⏱️ **Max Shift Time**: **6 Hours** per driver limit.
        * 🔄 **Round-Trip**: Includes time to return to depot.
        """,
        "err_limit_stops": "⚠️ You entered {count} stops, which exceeds the maximum limit of 30! Please reduce the locations.",
        "err_no_solution": "❌ Algorithm could not find a feasible solution. Try adding more drivers!",
        "kpi_stops": "📦 Total Stops",
        "kpi_drivers": "🚚 Active Drivers",
        "kpi_max_time": "⏱️ Max Shift Time (Inc. Return)",
        "kpi_total_time": "📊 Total Cumulative Time",
        "map_title": "🗺️ Live Route Overview (Round Trip)",
        "list_title": "📱 Driver Dispatch & Navigation",
        "driver_label": "🚚 Driver {id}",
        "driver_est_time": "Est. Total Shift Time: {time} mins (Inc. Return)",
        "stop_label": "Stop {id}",
        "return_label": "🏁 Final Stop (Return to Depot)",
        "btn_gmaps": "🗺️ Google Maps",
        "btn_waze": "🚙 Waze Nav",
        "btn_gmaps_return": "🗺️ Return Google Maps",
        "btn_waze_return": "🚙 Return Waze Nav",
        "info_prompt": "👈 Please open the sidebar and click 【Generate Optimal Routes】!",
        "debug_title": "🐞 Streamlit Web API Diagnostic Panel",
        "units_stops": "stops",
        "units_drivers": "drivers",
        "units_mins": "mins",
    },
    "中文": {
        "title": "🚚 Smart Route AI 智能调度系统",
        "subtitle": "商业级 API 驱动 | 支持返程闭环与多语言自适应",
        "sidebar_title": "🚚 调度控制中心",
        "sidebar_caption": "商业级多司机排单算法平台",
        "lang_select": "🌐 选择语言 / Language",
        "depot_label": "🏭 发货起点 (仓库/餐厅):",
        "stops_label": "📍 配送目的地 (每行一个):",
        "fleet_header": "🚚 运力参数设置",
        "drivers_count": "司机人数",
        "service_time": "卸货耗时(分)",
        "btn_submit": "⚡ 一键生成最佳调度方案",
        "rules_title": "ℹ️ 系统规则与参数上限说明",
        "rules_body": """
        * 📍 **最多送货点**：上限 **30 个地点**（超出自动拦截）。
        * 👥 **最多司机数**：支持 **1 ~ 6 位司机**。
        * ⏱️ **单人最长工时**：每位司机上限 **6 小时**（含返程）。
        * 🔄 **闭环返程计算**：已强制包含司机返回仓库的时间。
        """,
        "err_limit_stops": "⚠️ 当前输入了 {count} 个送货地点，超过了系统允许上限（最多 30 个）！请减少地点。",
        "err_no_solution": "❌ 运筹算法未能求解出方案，请尝试增加司机人数！",
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
        "info_prompt": "👈 请在侧边栏输入配送地点，点击【一键生成最佳调度方案】！",
        "debug_title": "🐞 Streamlit 网页 API 诊断面板",
        "units_stops": "个",
        "units_drivers": "位",
        "units_mins": "分钟",
    },
    "Bahasa Melayu": {
        "title": "🚚 Sistem Smart Route AI",
        "subtitle": "Pengoptimum Laluan AI Komersial | Sokongan Perjalanan Pergi-Balik",
        "sidebar_title": "🚚 Pusat Kawalan Penghantaran",
        "sidebar_caption": "Platform Pengatur Laluan Pemandu",
        "lang_select": "🌐 Pilih Bahasa / Select Language",
        "depot_label": "🏭 Depot / Lokasi Permulaan:",
        "stops_label": "📍 Destinasi Penghantaran (Satu setiap baris):",
        "fleet_header": "🚚 Tetapan Kapasiti",
        "drivers_count": "Bilangan Pemandu",
        "service_time": "Masa Memunggah (min)",
        "btn_submit": "⚡ Hasilkan Laluan Optimal",
        "rules_title": "ℹ️ Peraturan & Had Sistem",
        "rules_body": """
        * 📍 **Maksimum Lokasi**: Hingga **30 lokasi**.
        * 👥 **Maksimum Pemandu**: Menyokong **1 ~ 6 pemandu**.
        * ⏱️ **Masa Kerja Maksimum**: **6 Jam** setiap pemandu.
        * 🔄 **Perjalanan Balik**: Termasuk masa kembali ke depot.
        """,
        "err_limit_stops": "⚠️ Anda memasukkan {count} lokasi, melebihi had maksimum 30! Sila kurangkan lokasi.",
        "err_no_solution": "❌ Algoritma tidak menemui penyelesaian. Sila tambah pemandu!",
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
        "info_prompt": "👈 Sila masukkan lokasi di bar sampingan dan tekan 【Hasilkan Laluan Optimal】!",
        "debug_title": "🐞 Panel Diagnosis API Streamlit",
        "units_stops": "lokasi",
        "units_drivers": "pemandu",
        "units_mins": "minit",
    },
    "Bahasa Sarawak": {
        "title": "🚚 Sistem Smart Route AI Sarawak",
        "subtitle": "Sistem Susun Jalan Pok Driver Penghantaran | Pusing Balik Gudang",
        "sidebar_title": "🚚 Kawalan Penghantaran",
        "sidebar_caption": "Sistem Susun Jalan Driver Kuching",
        "lang_select": "🌐 Pilih Bahasa / Select Language",
        "depot_label": "🏭 Gudang / Tempat Mula:",
        "stops_label": "📍 Lokasi Hantar Barang (Satu baris satu tempat):",
        "fleet_header": "🚚 Tetapan Driver",
        "drivers_count": "Jumlah Driver",
        "service_time": "Masa Punggah Barang (minit)",
        "btn_submit": "⚡ Susun Jalan Paling Ngam",
        "rules_title": "ℹ️ Syarat & Had Sistem",
        "rules_body": """
        * 📍 **Paling Banyak Lokasi**: Sampai **30 tempat** ajak.
        * 👥 **Paling Banyak Driver**: Boleh **1 ~ 6 orang driver**.
        * ⏱️ **Masa Kerja Driver**: Paling lapan **6 Jam** sorang (sekali balek gudang).
        * 🔄 **Kira Masa Balek**: Sudah kira sekali masa driver balek ke gudang.
        """,
        "err_limit_stops": "⚠️ Aie, kita masok {count} tempat, dah lebih had 30! Tolong kurangkan sikit lokasi ya.",
        "err_no_solution": "❌ Sik dapat carik jalan ngam lah! Cuba tambah driver agik.",
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
        "btn_gmaps_return": "🗺️ Google Maps Balek",
        "btn_waze_return": "🚙 Waze Nav Balek",
        "info_prompt": "👈 Tolong masokkan tempat kat tepi ya, lepas ya tekan 【Susun Jalan Paling Ngam】!",
        "debug_title": "🐞 Panel Diagnosis API",
        "units_stops": "biji",
        "units_drivers": "orang",
        "units_mins": "minit",
    },
}

# CSS 强制防死锁深色模式样式
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
    </style>
""",
    unsafe_allow_html=True,
)

if "calculated" not in st.session_state:
    st.session_state.calculated = False

# ---------------------------------------------------------------------------
# 3. 核心算法与地理解析函数
# ---------------------------------------------------------------------------
def geocode_address_locationiq_debug(address):
    url = f"https://us1.locationiq.com/v1/search?key={LOCATIONIQ_TOKEN.strip()}&q={urllib.parse.quote(address)}&format=json&countrycodes=my"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        res = requests.get(url, headers=headers, timeout=6)
        status_code = res.status_code
        if status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                lng = float(data[0]["lon"])
                lat = float(data[0]["lat"])
                display_name = data[0].get("display_name", address)
                return [lng, lat], display_name, {"status": 200, "msg": "Success", "raw": data[0]}
            else:
                return None, None, {"status": 200, "msg": "返回列表为空", "raw": res.text}
        else:
            return None, None, {"status": status_code, "msg": f"HTTP Error {status_code}", "raw": res.text}
    except Exception as e:
        return None, None, {"status": 0, "msg": "请求异常", "raw": str(e)}


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
# 4. 页面侧边栏（Sidebar）：语言切换与参数设置
# ---------------------------------------------------------------------------
with st.sidebar:
    # 🌐 语言选择框（默认 English）
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

    stops_input = st.text_area(
        L["stops_label"],
        "Vivacity Megamall, Kuching, Sarawak\nSwinburne University Kuching, Sarawak\nThe Spring Shopping Mall, Kuching\nPlaza Merdeka, Kuching, Sarawak\nAEON Mall Kuching Central, Sarawak",
        height=180,
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
# 5. 主页面区域
# ---------------------------------------------------------------------------
st.markdown(
    f'<div class="main-header">{L["title"]}</div>',
    unsafe_allow_html=True,
)
st.caption(L["subtitle"])
st.divider()

if btn_submit:
    stops_list = [
        line.strip() for line in stops_input.split("\n") if line.strip()
    ]

    if len(stops_list) > 30:
        st.error(L["err_limit_stops"].format(count=len(stops_list)))
    else:
        all_locations = [depot_input] + stops_list
        total_count = len(all_locations)

        coords = []
        valid_locations = []
        failed_locations = []
        debug_logs = []

        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, loc in enumerate(all_locations):
            status_text.text(f"⚡ Loading {idx+1}/{total_count}: {loc}")
            progress_bar.progress((idx + 1) / total_count)

            c, full_addr, log_info = geocode_address_locationiq_debug(loc)
            debug_logs.append({"address": loc, "log": log_info})

            if c:
                coords.append(c)
                valid_locations.append(loc)
            else:
                failed_locations.append(loc)

            time.sleep(0.3)

        status_text.empty()
        progress_bar.empty()

        if failed_locations:
            st.warning(
                f"⚠️ Skipping unreachable stops: {', '.join(failed_locations)}"
            )

        if len(coords) >= 2:
            with st.spinner("🚀 Calculating optimal routes..."):
                service_times_sec = [0] + [service_time_min * 60] * (
                    len(coords) - 1
                )
                time_matrix = get_time_matrix(coords)
                routes = solve_vrp_multi_vehicle(
                    time_matrix, service_times_sec, num_drivers
                )

                if routes:
                    st.session_state.calculated = True
                    st.session_state.valid_locations = valid_locations
                    st.session_state.coords = coords
                    st.session_state.routes = routes
                    st.session_state.time_matrix = time_matrix
                    st.session_state.service_times_sec = service_times_sec
                else:
                    st.error(L["err_no_solution"])

# 渲染数据看板
if st.session_state.calculated:
    valid_locations = st.session_state.valid_locations
    coords = st.session_state.coords
    routes = st.session_state.routes
    time_matrix = st.session_state.time_matrix
    service_times_sec = st.session_state.service_times_sec

    total_stops = len(valid_locations) - 1
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

    # 2x2 指标看板
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
            tooltip="🏭 Depot",
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
            folium.PolyLine(
                path_coords, color=color, weight=5, opacity=0.85
            ).add_to(m)

        st_folium(m, width="100%", height=400, key="v25_multilang_map")

    with col_list:
        st.subheader(L["list_title"])

        for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
            color = colors[driver_idx % len(colors)]
            v_time_sec = sum(
                time_matrix[route[i]][route[i + 1]] + service_times_sec[route[i + 1]]
                for i in range(len(route) - 1)
            )

            driver_title = L["driver_label"].format(id=vehicle_id + 1)
            driver_time_str = L["driver_est_time"].format(
                time=round(v_time_sec / 60, 1)
            )

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

            # 返程按钮卡片
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
else:
    st.info(L["info_prompt"])