import folium
from geopy.geocoders import Nominatim
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import streamlit as st
from streamlit_folium import st_folium

# ---------------------------------------------------------------------------
# 1. 页面基本配置
# ---------------------------------------------------------------------------
st.set_page_config(page_title="智能送货路线优化系统", page_icon="🚚", layout="wide")

st.title("🚚 智能送货路径优化系统 (Best Route Optimization)")
st.caption("基于 OSRM 开源引擎与 OR-Tools 运筹算法，以【最短时间】为核心自动排单")

# 初始化 session state 用于存储计算结果
if "calculated" not in st.session_state:
    st.session_state.calculated = False

# ---------------------------------------------------------------------------
# 2. 核心算法函数
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def geocode_address(address):
    """将文本地址转换为 GPS 经纬度"""
    geolocator = Nominatim(user_agent="my_delivery_route_app_v3")
    location = geolocator.geocode(address)
    if location:
        return [location.longitude, location.latitude], location.address
    return None, None

def get_time_matrix_and_route(coords):
    """调用 OSRM 获取时间矩阵"""
    coord_str = ";".join([f"{c[0]},{c[1]}" for c in coords])
    table_url = f"http://router.project-osrm.org/table/v1/driving/{coord_str}?annotations=duration"
    res = requests.get(table_url, headers={"User-Agent": "MyDeliveryOptimizer/1.0"})
    time_matrix = [[int(cell) for cell in row] for row in res.json()["durations"]]
    return time_matrix

def solve_vrp(time_matrix, service_times):
    """使用 OR-Tools 求解最短时间路线"""
    num_locs = len(time_matrix)
    manager = pywrapcp.RoutingIndexManager(num_locs, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return time_matrix[from_node][to_node] + service_times[to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(search_parameters)
    
    route_order = []
    if solution:
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route_order.append(node)
            index = solution.Value(routing.NextVar(index))
        route_order.append(manager.IndexToNode(index))
    return route_order

# ---------------------------------------------------------------------------
# 3. Streamlit 网页前端界面逻辑
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📋 输入配送地点")
    
    depot_input = st.text_input("📍 1. 发货起点 (餐厅/仓库):", "Kuching Waterfront, Sarawak, Malaysia")
    
    stops_input = st.text_area(
        "📍 2. 送货目的地列表 (每行一个地址):",
        "Vivacity Megamall, Kuching, Sarawak\nSwinburne University Kuching, Sarawak\nThe Spring Shopping Mall, Kuching",
        height=120
    )
    
    service_time_min = st.number_input("⏱️ 每个点预计卸货耗时 (分钟):", min_value=1, max_value=30, value=5)
    
    btn_submit = st.button("🚀 开始一键优化路线", type="primary", use_container_width=True)

# 当用户按下按钮时触发计算，并保存在 session_state 中
if btn_submit:
    stops_list = [line.strip() for line in stops_input.split("\n") if line.strip()]
    all_locations = [depot_input] + stops_list
    
    with st.spinner("正在解析地址与计算最优路线..."):
        coords = []
        valid_locations = []
        for loc in all_locations:
            c, full_addr = geocode_address(loc)
            if c:
                coords.append(c)
                valid_locations.append(loc)
        
        if len(coords) >= 2:
            service_times_sec = [0] + [service_time_min * 60] * (len(coords) - 1)
            time_matrix = get_time_matrix_and_route(coords)
            best_order = solve_vrp(time_matrix, service_times_sec)
            
            # 将结果写入 state
            st.session_state.calculated = True
            st.session_state.valid_locations = valid_locations
            st.session_state.coords = coords
            st.session_state.best_order = best_order
            st.session_state.time_matrix = time_matrix
            st.session_state.service_times_sec = service_times_sec

# 渲染地图和路线信息
if st.session_state.calculated:
    valid_locations = st.session_state.valid_locations
    coords = st.session_state.coords
    best_order = st.session_state.best_order
    time_matrix = st.session_state.time_matrix
    service_times_sec = st.session_state.service_times_sec

    with col_right:
        st.subheader("🗺️ 最佳路线规划结果")
        
        # 计算全程总耗时
        total_sec = 0
        for i in range(len(best_order) - 1):
            u, v = best_order[i], best_order[i+1]
            total_sec += time_matrix[u][v] + service_times_sec[v]
        
        st.success(f"🎉 路线规划完成！全程预计花费时间: **{round(total_sec / 60, 1)} 分钟**")
        
        # 地图初始化
        center_lat, center_lng = coords[0][1], coords[0][0]
        m = folium.Map(location=[center_lat, center_lng], zoom_start=13)
        
        # 绘制 Marker 标记点
        route_points = []
        for step_idx, node_idx in enumerate(best_order[:-1]):
            lng, lat = coords[node_idx]
            route_points.append([lat, lng])
            
            label_name = "起点 (仓库)" if node_idx == 0 else f"第 {step_idx} 站: {valid_locations[node_idx]}"
            color = "red" if node_idx == 0 else "blue"
            
            folium.Marker(
                [lat, lng],
                popup=label_name,
                tooltip=f"{step_idx}. {valid_locations[node_idx]}",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
        
        # 连线
        route_points.append([coords[0][1], coords[0][0]])
        folium.PolyLine(route_points, color="crimson", weight=4, opacity=0.8).add_to(m)
        
        # 渲染地图（使用固定 key 阻止无意义重绘）
        st_folium(m, width=700, height=450, key="delivery_map")
        
        st.markdown("### 📌 详细送货顺序清单：")
        st.write(" ➔ ".join([valid_locations[i] for i in best_order]))