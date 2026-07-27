import folium
from geopy.geocoders import Nominatim
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import streamlit as st
from streamlit_folium import st_folium
import urllib.parse

# ---------------------------------------------------------------------------
# 1. 页面基本配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="智能送货路线优化系统 V2.0", page_icon="🚚", layout="wide"
)

st.title("🚚 智能送货路径优化系统 V2.0")
st.caption(
    "支持【多司机分流排单】与【手机一键 Waze / Google Maps 导航】的算法控制台"
)

if "calculated" not in st.session_state:
    st.session_state.calculated = False


# ---------------------------------------------------------------------------
# 2. 核心算法与导航链接生成函数
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def geocode_address(address):
    """将文本地址转换为 GPS 经纬度"""
    geolocator = Nominatim(user_agent="my_delivery_route_app_v4")
    location = geolocator.geocode(address)
    if location:
        return [location.longitude, location.latitude], location.address
    return None, None


def get_time_matrix(coords):
    """调用 OSRM 获取时间矩阵"""
    coord_str = ";".join([f"{c[0]},{c[1]}" for c in coords])
    table_url = f"http://router.project-osrm.org/table/v1/driving/{coord_str}?annotations=duration"
    res = requests.get(
        table_url, headers={"User-Agent": "MyDeliveryOptimizer/2.0"}
    )
    return [[int(cell) for cell in row] for row in res.json()["durations"]]


def solve_vrp_multi_vehicle(time_matrix, service_times, num_vehicles):
    """使用 OR-Tools 求解多司机（Multi-Vehicle）最短时间路线"""
    num_locs = len(time_matrix)
    manager = pywrapcp.RoutingIndexManager(num_locs, num_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return time_matrix[from_node][to_node] + service_times[to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 增加维度，限制单车总时间（尽量平衡各个司机的负荷）
    routing.AddDimension(
        transit_callback_index,
        3600,  # 允许等待超时阈值
        14400,  # 每一个司机的最大工作时长 (4小时)
        True,  # 强制从零开始计时间
        "Time",
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

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
            # 只有当司机有任务时（不只停留在起点）才计入
            if len(route) > 2:
                routes[vehicle_id] = route
    return routes


def build_nav_urls(dest_name, lat, lng):
    """生成一键唤起 Google Maps 和 Waze 的 Universal Links"""
    encoded_name = urllib.parse.quote(dest_name)
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&destination_place_id={encoded_name}"
    waze_url = f"https://waze.com/ul?ll={lat},{lng}&navigate=yes"
    return gmaps_url, waze_url


# ---------------------------------------------------------------------------
# 3. Streamlit 网页 UI
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📋 运力与送货清单")

    depot_input = st.text_input(
        "📍 发货起点 (餐厅/仓库):",
        "Kuching Waterfront, Sarawak, Malaysia",
    )

    stops_input = st.text_area(
        "📍 送货目的地列表 (每行一个地址):",
        "Vivacity Megamall, Kuching, Sarawak\nSwinburne University Kuching, Sarawak\nThe Spring Shopping Mall, Kuching\nPlaza Merdeka, Kuching, Sarawak\nAEON Mall Kuching Central, Sarawak",
        height=150,
    )

    col_v, col_s = st.columns(2)
    with col_v:
        num_drivers = st.number_input(
            "🚚 出动司机人数:", min_value=1, max_value=5, value=2
        )
    with col_s:
        service_time_min = st.number_input(
            "⏱️ 卸货耗时 (分钟):", min_value=1, max_value=30, value=5
        )

    btn_submit = st.button(
        "🚀 开始多车辆智能派单", type="primary", use_container_width=True
    )

if btn_submit:
    stops_list = [
        line.strip() for line in stops_input.split("\n") if line.strip()
    ]
    all_locations = [depot_input] + stops_list

    with st.spinner("正在请求路况与多路线优化算法..."):
        coords = []
        valid_locations = []
        for loc in all_locations:
            c, full_addr = geocode_address(loc)
            if c:
                coords.append(c)
                valid_locations.append(loc)

        if len(coords) >= 2:
            service_times_sec = [0] + [service_time_min * 60] * (
                len(coords) - 1
            )
            time_matrix = get_time_matrix(coords)
            routes = solve_vrp_multi_vehicle(
                time_matrix, service_times_sec, num_drivers
            )

            st.session_state.calculated = True
            st.session_state.valid_locations = valid_locations
            st.session_state.coords = coords
            st.session_state.routes = routes
            st.session_state.time_matrix = time_matrix
            st.session_state.service_times_sec = service_times_sec

# 渲染计算结果
if st.session_state.calculated:
    valid_locations = st.session_state.valid_locations
    coords = st.session_state.coords
    routes = st.session_state.routes
    time_matrix = st.session_state.time_matrix
    service_times_sec = st.session_state.service_times_sec

    with col_right:
        st.subheader("🗺️ 司机分流派单路线图")

        # 初始化地图
        center_lat, center_lng = coords[0][1], coords[0][0]
        m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

        # 定义多位司机的路线专属颜色
        colors = ["blue", "green", "purple", "orange", "darkred"]

        # 标记发货仓库
        folium.Marker(
            [coords[0][1], coords[0][0]],
            popup="总仓库 / 发货点",
            tooltip="📍 起点/仓库",
            icon=folium.Icon(color="red", icon="home"),
        ).add_to(m)

        for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
            color = colors[driver_idx % len(colors)]
            route_points = []

            for step_idx, node_idx in enumerate(route[:-1]):
                if node_idx == 0:
                    continue
                lng, lat = coords[node_idx]
                route_points.append([lat, lng])

                folium.Marker(
                    [lat, lng],
                    popup=f"司机 {vehicle_id + 1} - 站 {step_idx}: {valid_locations[node_idx]}",
                    tooltip=f"🚚 司机 {vehicle_id + 1} | 站 {step_idx}: {valid_locations[node_idx]}",
                    icon=folium.Icon(color=color, icon="info-sign"),
                ).add_to(m)

            # 画线 (连接起点与各个目的地)
            path_coords = [[coords[node][1], coords[node][0]] for node in route]
            folium.PolyLine(
                path_coords, color=color, weight=4, opacity=0.8
            ).add_to(m)

        st_folium(m, width=700, height=420, key="multi_delivery_map")

        # 显示每个司机的派单与一键导航
        st.markdown("### 📱 各司机派单列表与一键导航")

        for driver_idx, (vehicle_id, route) in enumerate(routes.items()):
            # 计算该司机的耗时
            v_time_sec = sum(
                time_matrix[route[i]][route[i + 1]] + service_times_sec[route[i + 1]]
                for i in range(len(route) - 1)
            )

            with st.expander(
                f"🚚 司机 {vehicle_id + 1} 派单路线（共 {len(route)-2} 个送到点，预计耗时: {round(v_time_sec/60, 1)} 分钟）",
                expanded=True,
            ):
                for step_idx, node_idx in enumerate(route[1:-1], start=1):
                    loc_name = valid_locations[node_idx]
                    lng, lat = coords[node_idx]
                    gmaps_url, waze_url = build_nav_urls(loc_name, lat, lng)

                    col_info, col_btn1, col_btn2 = st.columns([3, 1, 1])
                    with col_info:
                        st.markdown(f"**第 {step_idx} 站**: {loc_name}")
                    with col_btn1:
                        st.link_button(
                            "🗺️ Google Maps",
                            gmaps_url,
                            use_container_width=True,
                        )
                    with col_btn2:
                        st.link_button(
                            "🚙 Waze 导航", waze_url, use_container_width=True
                        )