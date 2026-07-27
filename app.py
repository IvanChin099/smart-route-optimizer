import math
import time
import urllib.parse
import folium
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# 1. 页面基本配置与移动端/深色模式兼容 CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Route AI - 智能送货调度系统",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="collapsed", # 手机端默认折叠侧边栏
)

# 注入全局兼容 CSS，防止深色模式下文字“隐形”
st.markdown(
    """
    <style>
    /* 强制适配深色与浅色模式，防止文字看不见 */
    .stApp {
        background-color: #f8f9fa !important;
    }
    
    /* 标语与文字强行显示深色 */
    p, span, label, div {
        color: #1f2937 !important;
    }
    
    /* 标题渐变 */
    .main-header {
        font-size: 1.8rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF8F00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    /* 手机端卡片美化 */
    .mobile-card {
        background-color: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* 指标数字美化 */
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

LOCATIONIQ_TOKEN = "pk.e792503785b6b6cebd3c6c52b40b8d45"

# ---------------------------------------------------------------------------
# 2. 核心算法与地理解析函数
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
    """离线多维距离矩阵"""
    num_locs = len(coords)
    matrix = [[0] * num_locs for _ in range(num_locs)]
    AVERAGE_SPEED_MPS = 9.72  # ~35 km/h
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
        21600,  # 6小时上限
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
# 3. 页面侧边栏（Sidebar）
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🚚 调度控制中心")
    st.caption("商业级多司机排单算法平台")
    st.divider()

    depot_input = st.text_input(
        "🏭 发货起点 (仓库/餐厅):",
        "Kuching Waterfront, Sarawak, Malaysia",
    )

    stops_input = st.text_area(
        "📍 配送目的地 (每行一个):",
        "Vivacity Megamall, Kuching, Sarawak\nSwinburne University Kuching, Sarawak\nThe Spring Shopping Mall, Kuching\nPlaza Merdeka, Kuching, Sarawak\nAEON Mall Kuching Central, Sarawak",
        height=180,
    )

    st.subheader("🚚 运力参数设置")
    col_v, col_s = st.columns(2)
    with col_v:
        num_drivers = st.number_input(
            "司机人数", min_value=1, max_value=6, value=3
        )
    with col_s:
        service_time_min = st.number_input(
            "卸货耗时(分)", min_value=1, max_value=30, value=5
        )

    st.divider()
    btn_submit = st.button(
        "⚡ 一键生成最佳调度方案", type="primary", use_container_width=True
    )

    with st.expander("ℹ️ 系统规则与参数上限说明"):
        st.markdown(
            """
            * 📍 **最多送货点**：上限 **30 个地点**。
            * 👥 **最多司机数**：支持 **1 ~ 6 位司机**。
            * ⏱️ **单人最长工时**：每位司机上限 **6 小时**。
            * 🔄 **闭环返程计算**：已强制包含返回仓库的时间。
            """
        )

# ---------------------------------------------------------------------------
# 4. 页面主区域（Main Canvas）
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="main-header">🚚 Smart Route AI 智能调度系统</div>',
    unsafe_allow_html=True,
)
st.caption("商业级 API 驱动 | 支持返程闭环与移动端自适应")
st.divider()

if btn_submit:
    stops_list = [
        line.strip() for line in stops_input.split("\n") if line.strip()
    ]
    
    if len(stops_list) > 30:
        st.error(f"⚠️ 当前输入了 {len(stops_list)} 个送货地点，超过了系统允许上限（最多 30 个）！请减少地点后重新计算。")
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
            status_text.text(f"⚡ 解析中 {idx+1}/{total_count}: {loc}")
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
                f"⚠️ 有 {len(failed_locations)} 个地址无法定位，已自动跳过：{', '.join(failed_locations)}"
            )

        if len(coords) >= 2:
            with st.spinner("🚀 地理坐标已就位！OR-Tools 运筹算法正在求解最佳路线..."):
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
                    st.error("❌ 运筹算法未能求解出方案，请尝试增加司机人数！")

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

    # ⚡ 手机端优化：2x2 网格卡片布局，避免被拉成一条直线
    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        st.metric("📦 待送货点", f"{total_stops} 个")
    with r1_col2:
        st.metric("🚚 出动司机", f"{active_drivers} 位")

    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        st.metric("⏱️ 方案最长耗时", f"{max_time_min} 分钟")
    with r2_col2:
        st.metric("📊 累积总耗时", f"{total_time_min} 分钟")

    st.markdown("<br>", unsafe_allow_html=True)

    col_map, col_list = st.columns([1.2, 1])
    colors = ["blue", "green", "purple", "orange", "darkred", "cadetblue"]

    with col_map:
        st.subheader("🗺️ 全局实景路线看板")
        center_lat, center_lng = coords[0][1], coords[0][0]
        m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

        folium.Marker(
            [coords[0][1], coords[0][0]],
            popup="起点仓库 (发货/返程中心)",
            tooltip="🏭 发货仓库",
            icon=folium.Icon(color="red", icon="home"),
        ).add_to(m)

        for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
            color = colors[driver_idx % len(colors)]
            for step_idx, node_idx in enumerate(route[1:-1], start=1):
                lng, lat = coords[node_idx]
                folium.Marker(
                    [lat, lng],
                    popup=f"司机 {vehicle_id + 1} - 站 {step_idx}: {valid_locations[node_idx]}",
                    tooltip=f"🚚 司机 {vehicle_id + 1} | 站 {step_idx}",
                    icon=folium.Icon(color=color, icon="info-sign"),
                ).add_to(m)

            path_coords = [[coords[node][1], coords[node][0]] for node in route]
            folium.PolyLine(
                path_coords, color=color, weight=5, opacity=0.85
            ).add_to(m)

        st_folium(m, width="100%", height=400, key="v25_mobile_map")

    with col_list:
        st.subheader("📱 司机派单与导航中心")

        for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
            color = colors[driver_idx % len(colors)]
            v_time_sec = sum(
                time_matrix[route[i]][route[i + 1]] + service_times_sec[route[i + 1]]
                for i in range(len(route) - 1)
            )

            # ⚡ 手机端带卡片的清晰样式
            st.markdown(
                f"""
                <div class="mobile-card">
                    <h3 style="margin:0; color:#1f2937;">🚚 司机 {vehicle_id + 1}</h3>
                    <p style="margin:5px 0 0 0; color:#4b5563; font-weight:bold;">全程预计耗时: {round(v_time_sec/60, 1)} 分钟 (含返程)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for step_idx, node_idx in enumerate(route[1:-1], start=1):
                loc_name = valid_locations[node_idx]
                lng, lat = coords[node_idx]
                gmaps_url, waze_url = build_nav_urls(loc_name, lat, lng)

                st.markdown(f"**站 {step_idx}**: {loc_name}")
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    st.link_button("🗺️ Google Maps", gmaps_url, use_container_width=True)
                with btn_c2:
                    st.link_button("🚙 Waze 导航", waze_url, use_container_width=True)
                st.divider()

            # 返程站
            depot_name = valid_locations[0]
            depot_lng, depot_lat = coords[0]
            gmaps_depot, waze_depot = build_nav_urls(f"返程: {depot_name}", depot_lat, depot_lng)
            
            st.markdown(f"**🏁 终点站 (返回仓库)**: {depot_name}")
            btn_d1, btn_d2 = st.columns(2)
            with btn_d1:
                st.link_button("🗺️ 返程 Google Maps", gmaps_depot, use_container_width=True)
            with btn_d2:
                st.link_button("🚙 返程 Waze 导航", waze_depot, use_container_width=True)
            st.divider()
else:
    st.info("👈 请打开左侧边栏（点击左上角 >> 图标）输入配送地点与司机人数，点击【一键生成最佳调度方案】！")