"""Streamlit前端应用 - 案例知识点匹配系统"""

import streamlit as st
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.pdf_converter import PDFConverter

# ==================== 页面配置 ====================

st.set_page_config(
    page_title="案例知识点匹配系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .subsection-header {
        font-size: 1.2rem;
        font-weight: 500;
        color: #34495e;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .info-box {
        background-color: #e8f4f8;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# API端点配置
import os
API_BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")

# ==================== 工具函数 ====================

def call_api(endpoint: str, method: str = "GET", data: Optional[Dict] = None, files: Optional[Dict] = None):
    """调用后端API"""
    url = f"{API_BASE_URL}{endpoint}"
    session = requests.Session()
    try:
        session.trust_env = False
    except Exception:
        pass

    try:
        if method == "GET":
            response = session.get(url, params=data, timeout=20)
        elif method == "POST":
            if files:
                response = session.post(url, data=data, files=files, timeout=120)
            else:
                response = session.post(url, json=data, timeout=60)
        else:
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确保API服务已启动 (端口 8000)")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API请求失败: {e}")
        return None
    except Exception as e:
        st.error(f"请求错误: {e}")
        return None

# ==================== 主界面 ====================

# 标题
st.markdown('<div class="main-header">案例知识点匹配系统</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">基于BGE-M3的案例理论知识点重复度检测与分析</div>', unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.markdown("### 功能选择")

    # 页面选择
    page = st.radio(
        "请选择功能模块",
        ["案例分析", "理论查询", "案例检索"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### 系统信息")

    # 获取系统状态
    health = call_api("/health")
    if health:
        st.success("系统运行正常")
        stats = call_api("/stats")
        if stats:
            st.metric("数据库案例数", stats.get('total_cases', 0))
            st.metric("理论知识点数", stats.get('total_theories', 0))
    else:
        st.error("系统离线")

# ==================== 页面路由 ====================

if page == "案例分析":
    # ==================== 案例分析页面 ====================
    st.markdown('<div class="section-header">案例输入</div>', unsafe_allow_html=True)

    # 输入方式选择
    input_method = st.radio(
        "选择输入方式",
        ["PDF文件上传", "文本输入"],
        horizontal=True,
        label_visibility="collapsed"
    )

    # 基本信息输入
    col1, col2 = st.columns(2)

    with col1:
        case_name = st.text_input("案例名称 *", placeholder="请输入案例名称")
        author = st.text_input("作者", placeholder="可选")
        subject = st.text_input("学科领域", placeholder="如：市场营销、战略管理等")

    with col2:
        industry = st.text_input("行业", placeholder="如：制造业、金融等")
        keywords = st.text_input("关键词", placeholder="多个关键词用逗号分隔")
        theories_input = st.text_input("主要理论 (可选)", placeholder="多个理论用逗号分隔，留空则自动识别")

    # 内容输入
    if input_method == "PDF文件上传":
        uploaded_file = st.file_uploader("上传PDF文件", type=['pdf'])

        if st.button("开始分析", type="primary", disabled=not (case_name and uploaded_file)):
            with st.spinner("正在分析案例..."):
                # 准备数据
                data = {"name": case_name}
                if author:
                    data["author"] = author
                if subject:
                    data["subject"] = subject
                if industry:
                    data["industry"] = industry
                if keywords:
                    data["keywords"] = keywords
                if theories_input:
                    data["primary_theories"] = theories_input  # 使用primary_theories字段

                # 准备文件
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")
                }

                # 调用API
                result = call_api("/analyze/upload", method="POST", data=data, files=files)

                if result:
                    st.session_state.analysis_result = result

    else:  # 文本输入
        case_text = st.text_area(
            "案例文本 *",
            height=300,
            placeholder="请输入或粘贴案例全文..."
        )

        if st.button("开始分析", type="primary", disabled=not (case_name and case_text)):
            with st.spinner("正在分析案例..."):
                # 准备数据
                data = {
                    "name": case_name,
                    "text": case_text
                }

                if author:
                    data["author"] = author
                if subject:
                    data["subject"] = subject
                if industry:
                    data["industry"] = industry
                if keywords:
                    data["keywords"] = keywords
                if theories_input:
                    data["primary_theories"] = [t.strip() for t in theories_input.split(",") if t.strip()]  # 使用primary_theories字段

                # 调用API
                result = call_api("/analyze/text", method="POST", data=data)

                if result:
                    st.session_state.analysis_result = result

    # ==================== 分析结果展示 ====================

    if hasattr(st.session_state, 'analysis_result'):
        st.markdown("---")
        st.markdown('<div class="section-header">分析结果</div>', unsafe_allow_html=True)

        result = st.session_state.analysis_result

        # 1. 创新度评分
        st.markdown('<div class="subsection-header">创新度评分</div>', unsafe_allow_html=True)

        innovation = result.get("innovation_score", {})
        score = innovation.get("innovation_score", 0)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("创新度总分", f"{score:.1f}", help="基于理论频率计算的创新度评分 (0-100)")
        with col2:
            novel_count = len(innovation.get("novel_theories", []))
            st.metric("新颖理论", f"{novel_count} 个", help="使用频次 ≤ 2次")
        with col3:
            common_count = len(innovation.get("common_theories", []))
            st.metric("常用理论", f"{common_count} 个", help="使用频次 3-7次")
        with col4:
            high_freq_count = len(innovation.get("high_frequency_theories", []))
            st.metric("高频理论", f"{high_freq_count} 个", help="使用频次 ≥ 8次")

        # 2. 理论匹配结果
        st.markdown('<div class="subsection-header">理论匹配结果</div>', unsafe_allow_html=True)

        theories = result.get("identified_theories", [])  # 系统自动识别的所有理论
        exact_matches = result.get("exact_matches", {})
        fuzzy_matches = result.get("fuzzy_matches", {})
        excel_matches = result.get("excel_matches", {})
        primary_theories_input = result.get("primary_theories", [])  # 用户输入的主要理论（原始输入）

        # 判断用户是否输入了主要理论
        has_primary = primary_theories_input and len(primary_theories_input) > 0

        # 找出主要理论在识别理论中的匹配项
        # 用户可能输入"swot"，但系统识别出"SWOT分析"
        primary_theories = []
        if has_primary:
            for input_theory in primary_theories_input:
                input_lower = input_theory.lower().strip()
                # 在所有识别的理论中查找匹配
                for theory in theories:
                    theory_lower = theory.lower()
                    # 更精确的匹配：输入的理论包含在识别理论中，或者识别理论包含输入的理论
                    if input_lower in theory_lower or theory_lower in input_lower:
                        if theory not in primary_theories:  # 避免重复添加
                            primary_theories.append(theory)

        if theories:
            exact_count = len(exact_matches)
            fuzzy_count = len(fuzzy_matches)

            # 统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("识别理论总数", len(theories))
            with col2:
                st.metric("数据库精确匹配", exact_count)
            with col3:
                st.metric("数据库模糊匹配", fuzzy_count)

            # 根据是否有主要理论采用不同的显示模式
            if has_primary and primary_theories:
                # 模式1: 有主要理论 - 分两部分显示
                st.markdown(f'<div class="success-box">已指定主要理论：{", ".join(primary_theories_input)} → 匹配到：{", ".join(primary_theories)}</div>', unsafe_allow_html=True)

                # 分离主要理论和其他理论
                primary_theory_set = set(primary_theories)
                other_theories = [t for t in theories if t not in primary_theory_set]

                # 显示统计信息
                if len(other_theories) > 0:
                    st.info(f"系统识别理论总数: {len(theories)} | 主要理论: {len(primary_theories)} | 其他理论: {len(other_theories)}")

                # 主要理论部分
                st.markdown('<div class="subsection-header" style="color: #e74c3c;">主要理论查重结果</div>', unsafe_allow_html=True)

                primary_exact_matches = {k: v for k, v in exact_matches.items() if k in primary_theory_set}
                primary_fuzzy_matches = {k: v for k, v in fuzzy_matches.items() if k in primary_theory_set}

                if primary_exact_matches or primary_fuzzy_matches:
                    tab1, tab2 = st.tabs(["精确匹配", "模糊匹配"])

                    with tab1:
                        if primary_exact_matches:
                            st.markdown('<div class="warning-box">以下主要理论在数据库中找到完全匹配，存在重复风险</div>', unsafe_allow_html=True)
                            for theory in primary_theories:
                                if theory in primary_exact_matches:
                                    match_info = primary_exact_matches[theory]
                                    cases = match_info.get('cases', [])
                                    with st.expander(f"**{theory}** - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})", expanded=True):
                                        if cases:
                                            st.markdown("#### 使用案例详情")
                                            case_details = []
                                            for case in cases:
                                                case_details.append({
                                                    "案例名称": case.get('name', 'N/A'),
                                                    "案例编号": case.get('code', 'N/A'),
                                                    "年份": case.get('year', 'N/A'),
                                                    "学科": case.get('subject', 'N/A'),
                                                    "行业": case.get('industry', 'N/A')
                                                })
                                            df_cases = pd.DataFrame(case_details)
                                            st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                            # 年份分布统计
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1
                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(min(len(year_counts), 5))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                        else:
                                            st.info("暂无案例详情")
                        else:
                            st.success("主要理论无精确匹配，重复风险较低")

                    with tab2:
                        if primary_fuzzy_matches:
                            st.markdown('<div class="warning-box">以下主要理论通过模糊匹配找到相似理论</div>', unsafe_allow_html=True)
                            for theory in primary_theories:
                                if theory in primary_fuzzy_matches:
                                    match_info = primary_fuzzy_matches[theory]
                                    input_theory = match_info.get('input_theory', theory)
                                    matched_theory = match_info.get('matched_theory', '')
                                    cases = match_info.get('cases', [])
                                    with st.expander(f"**{input_theory}** → {matched_theory} - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})", expanded=True):
                                        st.markdown(f"**输入理论:** {input_theory}")
                                        st.markdown(f"**匹配到:** {matched_theory}")
                                        st.markdown(f"**匹配方式:** 模糊匹配")
                                        if cases:
                                            st.markdown("#### 使用案例详情")
                                            case_details = []
                                            for case in cases:
                                                case_details.append({
                                                    "案例名称": case.get('name', 'N/A'),
                                                    "案例编号": case.get('code', 'N/A'),
                                                    "年份": case.get('year', 'N/A'),
                                                    "学科": case.get('subject', 'N/A'),
                                                    "行业": case.get('industry', 'N/A')
                                                })
                                            df_cases = pd.DataFrame(case_details)
                                            st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                            # 年份分布统计
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1
                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(min(len(year_counts), 5))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                        else:
                                            st.info("暂无案例详情")
                        else:
                            st.success("主要理论无模糊匹配")
                else:
                    st.success("主要理论在数据库中无匹配记录，创新性较高")

                # 其他理论部分
                if other_theories:
                    st.markdown("---")
                    st.markdown('<div class="subsection-header">其他理论查重结果</div>', unsafe_allow_html=True)

                    other_exact_matches = {k: v for k, v in exact_matches.items() if k in other_theories}
                    other_fuzzy_matches = {k: v for k, v in fuzzy_matches.items() if k in other_theories}

                    tab3, tab4 = st.tabs(["精确匹配", "模糊匹配"])

                    with tab3:
                        if other_exact_matches:
                            st.markdown('<div class="info-box">以下其他理论在数据库中找到完全匹配</div>', unsafe_allow_html=True)
                            for theory in other_theories:
                                if theory in other_exact_matches:
                                    match_info = other_exact_matches[theory]
                                    cases = match_info.get('cases', [])
                                    with st.expander(f"**{theory}** - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                        if cases:
                                            st.markdown("#### 使用案例详情")
                                            case_details = []
                                            for case in cases:
                                                case_details.append({
                                                    "案例名称": case.get('name', 'N/A'),
                                                    "案例编号": case.get('code', 'N/A'),
                                                    "年份": case.get('year', 'N/A'),
                                                    "学科": case.get('subject', 'N/A'),
                                                    "行业": case.get('industry', 'N/A')
                                                })
                                            df_cases = pd.DataFrame(case_details)
                                            st.dataframe(df_cases, use_container_width=True, hide_index=True)
                                        else:
                                            st.info("暂无案例详情")
                        else:
                            st.info("其他理论无精确匹配")

                    with tab4:
                        if other_fuzzy_matches:
                            st.markdown('<div class="info-box">以下其他理论通过模糊匹配找到相似理论</div>', unsafe_allow_html=True)
                            for theory in other_theories:
                                if theory in other_fuzzy_matches:
                                    match_info = other_fuzzy_matches[theory]
                                    input_theory = match_info.get('input_theory', theory)
                                    matched_theory = match_info.get('matched_theory', '')
                                    cases = match_info.get('cases', [])
                                    with st.expander(f"**{input_theory}** → {matched_theory} - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                        st.markdown(f"**输入理论:** {input_theory}")
                                        st.markdown(f"**匹配到:** {matched_theory}")
                                        st.markdown(f"**匹配方式:** 模糊匹配")
                                        if cases:
                                            st.markdown("#### 使用案例详情")
                                            case_details = []
                                            for case in cases:
                                                case_details.append({
                                                    "案例名称": case.get('name', 'N/A'),
                                                    "案例编号": case.get('code', 'N/A'),
                                                    "年份": case.get('year', 'N/A'),
                                                    "学科": case.get('subject', 'N/A'),
                                                    "行业": case.get('industry', 'N/A')
                                                })
                                            df_cases = pd.DataFrame(case_details)
                                            st.dataframe(df_cases, use_container_width=True, hide_index=True)
                                        else:
                                            st.info("暂无案例详情")
                        else:
                            st.info("其他理论无模糊匹配")
            elif has_primary and not primary_theories:
                # 用户输入了主要理论，但系统未识别到匹配的理论
                st.warning(f"您指定的主要理论（{', '.join(primary_theories_input)}）未在系统识别的理论中找到匹配项")
                st.info("提示：系统将按正常模式显示所有识别到的理论。可能原因：理论名称不完全匹配，请尝试精确输入理论全称。")

                # 按正常模式显示
                tab1, tab2 = st.tabs(["数据库精确匹配", "数据库模糊匹配"])

                with tab1:
                    if exact_count > 0:
                        st.markdown('<div class="info-box">以下理论在数据库中找到完全匹配。点击理论名称查看详细使用情况。</div>', unsafe_allow_html=True)

                        for theory in theories:
                            if theory in exact_matches:
                                match_info = exact_matches[theory]
                                cases = match_info.get('cases', [])

                                with st.expander(f"**{theory}** - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                    if cases:
                                        st.markdown("#### 使用案例详情")

                                        case_details = []
                                        for case in cases:
                                            case_details.append({
                                                "案例名称": case.get('name', 'N/A'),
                                                "案例编号": case.get('code', 'N/A'),
                                                "年份": case.get('year', 'N/A'),
                                                "学科": case.get('subject', 'N/A'),
                                                "行业": case.get('industry', 'N/A')
                                            })

                                        df_cases = pd.DataFrame(case_details)
                                        st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                        # 年份分布统计
                                        if case_details:
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1

                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(len(year_counts))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                    else:
                                        st.info("暂无案例详情")
                    else:
                        st.info("未找到精确匹配的理论")

                with tab2:
                    if fuzzy_count > 0:
                        st.markdown('<div class="info-box">以下理论通过模糊匹配找到了数据库中的相似理论。点击查看详细使用情况。</div>', unsafe_allow_html=True)

                        for theory in theories:
                            if theory in fuzzy_matches:
                                match_info = fuzzy_matches[theory]
                                input_theory = match_info.get('input_theory', theory)
                                matched_theory = match_info.get('matched_theory', '')
                                cases = match_info.get('cases', [])

                                with st.expander(f"**{input_theory}** → {matched_theory} - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                    st.markdown(f"**输入理论:** {input_theory}")
                                    st.markdown(f"**匹配到:** {matched_theory}")
                                    st.markdown(f"**匹配方式:** 模糊匹配")

                                    if cases:
                                        st.markdown("#### 使用案例详情")

                                        case_details = []
                                        for case in cases:
                                            case_details.append({
                                                "案例名称": case.get('name', 'N/A'),
                                                "案例编号": case.get('code', 'N/A'),
                                                "年份": case.get('year', 'N/A'),
                                                "学科": case.get('subject', 'N/A'),
                                                "行业": case.get('industry', 'N/A')
                                            })

                                        df_cases = pd.DataFrame(case_details)
                                        st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                        # 年份分布统计
                                        if case_details:
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1

                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(len(year_counts))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                    else:
                                        st.info("暂无案例详情")
                    else:
                        st.info("未找到模糊匹配的理论")
            else:
                # 模式2: 无主要理论 - 正常显示
                tab1, tab2 = st.tabs(["数据库精确匹配", "数据库模糊匹配"])

                with tab1:
                    if exact_count > 0:
                        st.markdown('<div class="info-box">以下理论在数据库中找到完全匹配。点击理论名称查看详细使用情况。</div>', unsafe_allow_html=True)

                        for theory in theories:
                            if theory in exact_matches:
                                match_info = exact_matches[theory]
                                cases = match_info.get('cases', [])

                                with st.expander(f"**{theory}** - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                    if cases:
                                        st.markdown("#### 使用案例详情")

                                        case_details = []
                                        for case in cases:
                                            case_details.append({
                                                "案例名称": case.get('name', 'N/A'),
                                                "案例编号": case.get('code', 'N/A'),
                                                "年份": case.get('year', 'N/A'),
                                                "学科": case.get('subject', 'N/A'),
                                                "行业": case.get('industry', 'N/A')
                                            })

                                        df_cases = pd.DataFrame(case_details)
                                        st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                        # 年份分布统计
                                        if case_details:
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1

                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(len(year_counts))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                    else:
                                        st.info("暂无案例详情")
                    else:
                        st.info("未找到精确匹配的理论")

                with tab2:
                    if fuzzy_count > 0:
                        st.markdown('<div class="info-box">以下理论通过模糊匹配找到了数据库中的相似理论。点击查看详细使用情况。</div>', unsafe_allow_html=True)

                        for theory in theories:
                            if theory in fuzzy_matches:
                                match_info = fuzzy_matches[theory]
                                input_theory = match_info.get('input_theory', theory)
                                matched_theory = match_info.get('matched_theory', '')
                                cases = match_info.get('cases', [])

                                with st.expander(f"**{input_theory}** → {matched_theory} - 使用 {len(cases)} 次 ({match_info.get('frequency_rank', '未知')})"):
                                    st.markdown(f"**输入理论:** {input_theory}")
                                    st.markdown(f"**匹配到:** {matched_theory}")
                                    st.markdown(f"**匹配方式:** 模糊匹配")

                                    if cases:
                                        st.markdown("#### 使用案例详情")

                                        case_details = []
                                        for case in cases:
                                            case_details.append({
                                                "案例名称": case.get('name', 'N/A'),
                                                "案例编号": case.get('code', 'N/A'),
                                                "年份": case.get('year', 'N/A'),
                                                "学科": case.get('subject', 'N/A'),
                                                "行业": case.get('industry', 'N/A')
                                            })

                                        df_cases = pd.DataFrame(case_details)
                                        st.dataframe(df_cases, use_container_width=True, hide_index=True)

                                        # 年份分布统计
                                        if case_details:
                                            years = [c.get('year', 'N/A') for c in cases]
                                            year_counts = {}
                                            for year in years:
                                                if year != 'N/A':
                                                    year_counts[year] = year_counts.get(year, 0) + 1

                                            if year_counts:
                                                st.markdown("**年份分布:**")
                                                cols = st.columns(len(year_counts))
                                                for idx, (year, count) in enumerate(sorted(year_counts.items())):
                                                    with cols[idx]:
                                                        st.metric(year, f"{count} 次")
                                    else:
                                        st.info("暂无案例详情")
                    else:
                        st.info("未找到模糊匹配的理论")
        else:
            st.warning("未识别到理论知识点")

        # 3. 相似案例排名
        st.markdown('<div class="subsection-header">相似案例排名</div>', unsafe_allow_html=True)
        similar_cases = result.get("similar_cases", [])

        if similar_cases:
            st.markdown('<div class="info-box">根据综合相似度排序 (理论重叠40% + 语义相似度30% + 关键词20% + 学科10%)</div>', unsafe_allow_html=True)

            case_data = []
            for i, case in enumerate(similar_cases, 1):
                metadata = case.get("metadata", {})
                scores = case.get("scores", {})

                case_data.append({
                    "排名": i,
                    "案例名称": metadata.get("name", "N/A"),
                    "年份": metadata.get("year", "N/A"),
                    "综合相似度": f"{scores.get('final_score', 0):.3f}",
                    "语义相似度": f"{scores.get('semantic_similarity', 0):.3f}",
                    "学科": metadata.get("subject", "N/A")
                })

            df = pd.DataFrame(case_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("未找到相似案例")

        # 4. 完整报告
        st.markdown('<div class="subsection-header">完整分析报告</div>', unsafe_allow_html=True)
        with st.expander("查看Markdown格式报告"):
            report = result.get("report_markdown", "")
            st.markdown(report)

        # 下载报告按钮
        if report:
            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    label="下载Markdown格式",
                    data=report,
                    file_name=f"{case_name}_分析报告.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            with col2:
                try:
                    # 转换为PDF
                    pdf_bytes = PDFConverter.markdown_to_pdf(report)
                    st.download_button(
                        label="下载PDF格式",
                        data=pdf_bytes,
                        file_name=f"{case_name}_分析报告.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"PDF生成失败: {e}")

elif page == "理论查询":
    # ==================== 理论查询页面 ====================
    st.markdown('<div class="section-header">理论知识点查询</div>', unsafe_allow_html=True)

    # 获取理论列表
    theories_data = call_api("/theories/")

    if theories_data:
        # API直接返回列表,不是字典
        theories_list = theories_data if isinstance(theories_data, list) else []

        if theories_list:
            st.markdown('<div class="info-box">输入关键词搜索理论(支持模糊匹配,如输入"SWOT"可匹配"SWOT分析"、"SWOT分析法"等)</div>', unsafe_allow_html=True)

            # 搜索输入框
            search_keyword = st.text_input(
                "输入理论关键词",
                placeholder="如: SWOT, 蓝海, 波特五力...",
                help="支持大小写不敏感的模糊搜索"
            )

            # 过滤理论列表
            if search_keyword:
                keyword_lower = search_keyword.lower().strip()
                # 模糊匹配: 包含关键词即可
                filtered_theories = [
                    t for t in theories_list
                    if keyword_lower in t.lower()
                ]
            else:
                filtered_theories = theories_list

            # 显示统计信息
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"共找到 {len(filtered_theories)} 个匹配的理论")
            with col2:
                st.metric("理论总数", len(theories_list))

            # 显示匹配的理论列表
            if filtered_theories:
                # 如果只有一个匹配结果,自动选中
                if len(filtered_theories) == 1:
                    selected_theory = filtered_theories[0]
                    st.success(f"自动选中: {selected_theory}")
                else:
                    selected_theory = st.selectbox(
                        f"选择理论 (显示前100个)",
                        filtered_theories[:100],
                        index=0
                    )

                # 查询按钮
                if st.button("查询案例", type="primary"):
                    with st.spinner(f"正在查询理论 '{selected_theory}' 的案例..."):
                        # 调用API查询案例
                        result = call_api(f"/theories/{selected_theory}/cases")

                        if result:
                            st.session_state.theory_query_result = result
                            st.session_state.current_theory = selected_theory
            else:
                st.warning(f"未找到包含 '{search_keyword}' 的理论,请尝试其他关键词")

            # 显示查询结果
            if hasattr(st.session_state, 'theory_query_result') and hasattr(st.session_state, 'current_theory'):
                st.markdown("---")
                st.markdown('<div class="section-header">查询结果</div>', unsafe_allow_html=True)

                result = st.session_state.theory_query_result
                theory_name = st.session_state.current_theory

                st.markdown(f'<div class="subsection-header">理论: {theory_name}</div>', unsafe_allow_html=True)

                cases = result.get('cases', [])
                usage_count = result.get('usage_count', 0)
                frequency_rank = result.get('frequency_rank', '未知')

                # 统计信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("使用次数", usage_count)
                with col2:
                    st.metric("频率等级", frequency_rank)
                with col3:
                    if cases:
                        years = [c.get('year', 'N/A') for c in cases if c.get('year') != 'N/A']
                        year_range = f"{min(years)} - {max(years)}" if years else "N/A"
                        st.metric("年份范围", year_range)

                # 案例列表
                if cases:
                    st.markdown('<div class="subsection-header">使用案例详情</div>', unsafe_allow_html=True)

                    case_details = []
                    for case in cases:
                        case_details.append({
                            "案例名称": case.get('name', 'N/A'),
                            "案例编号": case.get('code', 'N/A'),
                            "年份": case.get('year', 'N/A'),
                            "学科": case.get('subject', 'N/A'),
                            "行业": case.get('industry', 'N/A'),
                            "关键词": case.get('keywords', 'N/A')
                        })

                    df_cases = pd.DataFrame(case_details)
                    st.dataframe(df_cases, use_container_width=True, hide_index=True)

                    # 统计分析
                    st.markdown('<div class="subsection-header">统计分析</div>', unsafe_allow_html=True)

                    # 年份分布
                    years = [c.get('year', 'N/A') for c in cases]
                    year_counts = {}
                    for year in years:
                        if year != 'N/A':
                            year_counts[year] = year_counts.get(year, 0) + 1

                    if year_counts:
                        st.markdown("**年份分布:**")
                        year_df = pd.DataFrame([
                            {"年份": year, "案例数": count}
                            for year, count in sorted(year_counts.items())
                        ])
                        st.bar_chart(year_df.set_index("年份"))

                    # 学科分布
                    subjects = [c.get('subject', 'N/A') for c in cases]
                    subject_counts = {}
                    for subj in subjects:
                        if subj != 'N/A':
                            subject_counts[subj] = subject_counts.get(subj, 0) + 1

                    if subject_counts:
                        st.markdown("**学科分布:**")
                        subject_df = pd.DataFrame([
                            {"学科": subj, "案例数": count}
                            for subj, count in sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
                        ])
                        st.dataframe(subject_df, use_container_width=True, hide_index=True)

                    # 行业分布
                    industries = [c.get('industry', 'N/A') for c in cases]
                    industry_counts = {}
                    for ind in industries:
                        if ind != 'N/A':
                            industry_counts[ind] = industry_counts.get(ind, 0) + 1

                    if industry_counts:
                        st.markdown("**行业分布:**")
                        industry_df = pd.DataFrame([
                            {"行业": ind, "案例数": count}
                            for ind, count in sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
                        ])
                        st.dataframe(industry_df, use_container_width=True, hide_index=True)
                else:
                    st.info("该理论暂无使用案例")
        else:
            st.warning("数据库中暂无理论数据")
    else:
        st.error("无法获取理论列表，请检查API服务")

elif page == "案例检索":
    # ==================== 案例检索页面 ====================
    st.markdown('<div class="section-header">案例检索</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">根据关键词、学科、行业、年份等条件检索数据库中的案例</div>', unsafe_allow_html=True)

    # 检索条件输入
    col1, col2 = st.columns(2)

    with col1:
        search_keyword = st.text_input("关键词", placeholder="案例名称或内容关键词")
        search_subject = st.text_input("学科", placeholder="如：市场营销、战略管理")

    with col2:
        search_industry = st.text_input("行业", placeholder="如：制造业、金融")
        search_year = st.text_input("年份", placeholder="如：2020 或 2018-2022")

    # 高级选项
    with st.expander("高级选项"):
        limit = st.slider("返回结果数量", min_value=10, max_value=100, value=50, step=10)

    # 检索按钮
    if st.button("开始检索", type="primary"):
        with st.spinner("正在检索案例..."):
            # 准备查询参数
            params = {}
            if search_keyword:
                params['keyword'] = search_keyword
            if search_subject:
                params['subject'] = search_subject
            if search_industry:
                params['industry'] = search_industry
            if search_year:
                params['year'] = search_year
            params['limit'] = limit

            # 调用API
            result = call_api("/cases/search", method="GET", data=params)

            if result:
                st.session_state.search_result = result

    # 显示检索结果
    if hasattr(st.session_state, 'search_result'):
        st.markdown("---")
        st.markdown('<div class="section-header">检索结果</div>', unsafe_allow_html=True)

        result = st.session_state.search_result
        cases = result.get('cases', [])
        total_count = result.get('total', 0)

        # 结果统计
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("找到案例", total_count)
        with col2:
            st.metric("显示案例", len(cases))
        with col3:
            if cases:
                has_theories = sum(1 for c in cases if c.get('theories'))
                st.metric("含理论标注", has_theories)

        # 案例列表
        if cases:
            st.markdown('<div class="subsection-header">案例列表</div>', unsafe_allow_html=True)

            for i, case in enumerate(cases, 1):
                with st.expander(f"**{i}. {case.get('name', 'N/A')}** - {case.get('code', 'N/A')}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**案例编号:** {case.get('code', 'N/A')}")
                        st.markdown(f"**年份:** {case.get('year', 'N/A')}")
                        st.markdown(f"**学科:** {case.get('subject', 'N/A')}")
                        st.markdown(f"**行业:** {case.get('industry', 'N/A')}")

                    with col2:
                        if case.get('author'):
                            st.markdown(f"**作者:** {case.get('author', 'N/A')}")
                        if case.get('keywords'):
                            st.markdown(f"**关键词:** {case.get('keywords', 'N/A')}")
                        if case.get('source'):
                            st.markdown(f"**来源:** {case.get('source', 'N/A')}")

                    # 理论标注
                    theories = case.get('theories', [])
                    if theories:
                        st.markdown("**理论标注:**")
                        theory_tags = " ".join([f"`{t}`" for t in theories])
                        st.markdown(theory_tags)

                    # 摘要或内容片段
                    if case.get('summary'):
                        st.markdown("**摘要:**")
                        st.markdown(case.get('summary', ''))

            # 下载结果
            if total_count > 0:
                st.markdown("---")
                st.markdown('<div class="subsection-header">导出结果</div>', unsafe_allow_html=True)

                # 准备CSV数据
                export_data = []
                for case in cases:
                    theories_str = ", ".join(case.get('theories', []))
                    export_data.append({
                        "案例名称": case.get('name', 'N/A'),
                        "案例编号": case.get('code', 'N/A'),
                        "年份": case.get('year', 'N/A'),
                        "学科": case.get('subject', 'N/A'),
                        "行业": case.get('industry', 'N/A'),
                        "作者": case.get('author', 'N/A'),
                        "关键词": case.get('keywords', 'N/A'),
                        "理论标注": theories_str
                    })

                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False, encoding='utf-8-sig')

                st.download_button(
                    label="下载CSV格式",
                    data=csv,
                    file_name="案例检索结果.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("未找到匹配的案例，请尝试调整检索条件")
