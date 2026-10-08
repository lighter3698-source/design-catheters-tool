import streamlit as st
import json
import os

st.set_page_config(
    page_title="心血管介入导管参数推导系统",
    page_icon="🫀",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. 配置与规则初始化
# -----------------------------------------------------------------------------
CONFIG_FILE = 'rules_config.json'

default_rules = {
    "expand_ratio": 1.05,       # 球囊额定直径扩张比例
    "balloon_margin": 3.0,     # 球囊额定长度两端余量
    "guidewire_clearance": 0.08,# 导管轴内径间隙
    "shaft_margin": 150.0,      # 导管轴长度余量
    "access_clearance": 0.5     # 入路安全间隙
}

if os.path.isfile(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            default_rules.update(user_config)
    except Exception:
        pass

# -----------------------------------------------------------------------------
# 2. 界面标题与侧边栏
# -----------------------------------------------------------------------------
st.title("🫀 冠脉介入导管设计参数智能推导系统")
st.caption("依据《临床通路数据字段表》与《字段-导管参数映射规则》自动推导")

with st.sidebar:
    st.header("⚙️ 规则推导系数设置")
    expand_ratio = st.slider("球囊扩张比例", 1.00, 1.10, float(default_rules["expand_ratio"]), step=0.01, key="sb_expand_ratio")
    balloon_margin = st.slider("球囊两端余量 (mm)", 2.0, 4.0, float(default_rules["balloon_margin"]), step=0.5, key="sb_balloon_margin")
    guidewire_clearance = st.slider("导丝腔配合间隙 (mm)", 0.05, 0.10, float(default_rules["guidewire_clearance"]), step=0.01, key="sb_guidewire_clearance")
    shaft_margin = st.slider("体外操控余量/导管余量 (mm)", 100.0, 200.0, float(default_rules["shaft_margin"]), step=10.0, key="sb_shaft_margin")
    access_clearance = st.slider("入路安全间隙 (mm)", 0.2, 1.0, float(default_rules["access_clearance"]), step=0.1, key="sb_access_clearance")

# -----------------------------------------------------------------------------
# 3. 临床通路数据输入（为所有组件配备了唯一的 key）
# -----------------------------------------------------------------------------
st.subheader("📋 临床通路数据输入")

tab1, tab2, tab3 = st.tabs(["1.1 血管通路与病变位置", "1.2 病变形态特征", "1.3 手术路径与入路"])

with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        vessel_name = st.selectbox("病变血管", ["LAD (左前降支)", "LCX (左回旋支)", "RCA (右冠状动脉)", "LM (左主干)", "大隐静脉桥", "内乳动脉桥"], key="input_vessel_name")
        vessel_segment = st.selectbox("病变段位", ["近段", "中段", "远段", "开口", "分叉"], key="input_vessel_segment")
    with col2:
        ref_vessel_diam = st.number_input("参考血管直径 (mm)", min_value=1.5, max_value=5.0, value=3.0, step=0.1, help="病变近远端正常血管内径均值", key="input_ref_vessel_diam")
        lesion_vessel_diam = st.number_input("靶病变血管内径 (mm)", min_value=1.0, max_value=5.0, value=2.2, step=0.1, key="input_lesion_vessel_diam")
    with col3:
        lesion_length = st.number_input("病变长度 (mm)", min_value=2.0, max_value=50.0, value=15.0, step=1.0, key="input_lesion_length")
        stenosis = st.slider("狭窄程度 (%)", 50, 99, 85, key="input_stenosis")

with tab2:
    col1, col2, col3 = st.columns(3)
    with col1:
        lesion_type = st.selectbox("病变类型 (ACC/AHA)", ["A型", "B1型", "B2型", "C型"], key="input_lesion_type")
        calcification = st.selectbox("钙化程度", ["无", "轻", "中", "重"], key="input_calcification")
    with col2:
        tortuosity = st.selectbox("血管弯曲度", ["轻", "中", "重"], key="input_tortuosity")
        bifurcation = st.radio("分叉病变", ["否", "是（累及分支）"], horizontal=True, key="input_bifurcation")
    with col3:
        cto_lesion = st.radio("CTO 病变 (慢性完全闭塞)", ["否", "是"], horizontal=True, key="input_cto")
        proximal_diam = st.number_input("病变近端血管内径 (mm)", value=3.2, step=0.1, key="input_proximal_diam")

with tab3:
    col1, col2, col3 = st.columns(3)
    with col1:
        access_route = st.selectbox("入路途径", ["桡动脉入路 (TRA)", "股动脉入路 (TFA)"], key="input_access_route")
    with col2:
        default_dist = 1000.0 if "桡动脉" in access_route else 300.0
        default_access_id = 2.5 if "桡动脉" in access_route else 6.0
        
        reach_distance = st.number_input("到达靶病变距离 (mm)", min_value=100.0, max_value=1500.0, value=default_dist, step=10.0, key="input_reach_distance")
    with col3:
        access_inner_diam = st.number_input("入路血管内径 (mm)", min_value=1.5, max_value=10.0, value=default_access_id, step=0.1, key="input_access_inner_diam")
        guidewire_spec = st.selectbox("拟匹配导丝规格", ["0.014 inch (0.36mm)", "0.018 inch", "0.035 inch"], key="input_guidewire_spec")

st.divider()

# -----------------------------------------------------------------------------
# 4. 自动规则推导计算
# -----------------------------------------------------------------------------
gw_diam_mm = 0.36 if "0.014" in guidewire_spec else (0.46 if "0.018" in guidewire_spec else 0.89)

# 推导1：球囊参数
balloon_nominal_diam = ref_vessel_diam * expand_ratio
balloon_nominal_len = lesion_length + balloon_margin

# 推导2：导管轴参数
shaft_max_od = max(0.5, access_inner_diam - access_clearance)
shaft_min_id = gw_diam_mm + guidewire_clearance
shaft_total_len = reach_distance + shaft_margin

# 推导3：整体参数
push_rod_len = shaft_total_len - balloon_nominal_len

# -----------------------------------------------------------------------------
# 5. 推导结果展示
# -----------------------------------------------------------------------------
st.header("🎯 导管设计参数推导结果")

res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.subheader("2.1 球囊参数")
    st.metric("球囊额定直径", f"{balloon_nominal_diam:.2f} mm", delta=f"基于参考直径×{expand_ratio}")
    st.metric("球囊额定长度", f"{balloon_nominal_len:.1f} mm", delta=f"病变长+{balloon_margin}mm")
    st.write(f"• **破裂直径估算**: ~{balloon_nominal_diam * 1.15:.2f} mm")
    st.write("• **推荐折叠翼数**: 3 翼" if balloon_nominal_diam >= 3.0 else "• **推荐折叠翼数**: 2 翼")

with res_col2:
    st.subheader("2.2 导管轴参数")
    st.metric("导管轴外径上限", f"{shaft_max_od:.2f} mm", delta=f"外径 ≤ 入路内径-{access_clearance}mm")
    st.metric("导管轴内径 (ID)", f"{shaft_min_id:.3f} mm", delta=f"≥ 导丝({gw_diam_mm}mm)+{guidewire_clearance}mm")
    st.metric("导管轴总长度", f"{shaft_total_len:.0f} mm", delta=f"到达距离+{shaft_margin}mm")

with res_col3:
    st.subheader("2.3 整体与结构参数")
    st.metric("有效长度", f"{shaft_total_len:.0f} mm")
    st.metric("推送杆长度", f"{push_rod_len:.1f} mm", delta="有效长度 - 球囊长")
    st.write(f"• **导丝腔内径**: {shaft_min_id:.3f} mm")
    
    if tortuosity == "重" or lesion_type == "C型":
        st.write("• **软硬度梯度**: 远端高柔顺（针对重度弯曲/高难度病变）")
    else:
        st.write("• **软硬度梯度**: 标准近硬远软梯度")

# -----------------------------------------------------------------------------
# 6. 安全校验与工程提示
# -----------------------------------------------------------------------------
st.divider()
st.subheader("⚠️ 安全与工艺校验提示")

check1, check2 = st.columns(2)

with check1:
    if balloon_nominal_diam > proximal_diam:
        st.error(f"❌ **过张风险**：推导出的球囊额定直径 ({balloon_nominal_diam:.2f}mm) 大于病变近端内径 ({proximal_diam}mm)，易引发夹层！")
    else:
        st.success("✅ **尺寸安全**：球囊额定直径在近端血管安全范围内。")

with check2:
    if calcification in ["中", "重"]:
        st.warning(f"⚠️ **病变钙化提示**：当前为【{calcification}度钙化】，建议提高球囊高额定破裂压（RBP），并考虑搭配高刚性导丝。")
    else:
        st.info("ℹ️ **病变状态**：软组织/无重度钙化，适用标准半顺应性/顺应性球囊。")
    