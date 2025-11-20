"""Streamlit 前端（新版映射与分组文案）

- 使用环境变量 API_URL 访问后端（默认 http://localhost:8000）
"""

import os
from typing import Dict, Optional
import requests
import streamlit as st
import pandas as pd


API_BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,::1")
SESSION = requests.Session()
try:
    SESSION.trust_env = False
except Exception:
    pass


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict] = None, files: Optional[Dict] = None):
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = SESSION.get(url, params=data, timeout=20)
        else:
            if files:
                resp = SESSION.post(url, data=data, files=files, timeout=120)
            else:
                resp = SESSION.post(url, json=data, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API 请求失败: {e}  (API: {API_BASE_URL})")
        return None


st.set_page_config(page_title="案例知识点匹配系统", layout="wide")

st.title("📚 案例知识点匹配系统")

with st.sidebar:
    st.markdown("### 功能选择")
    page = st.radio("请选择功能", ["案例分析", "理论查询", "案例检索"], label_visibility="collapsed")
    st.markdown("---")
    health = call_api("/health")
    if health:
        st.success("后端服务在线")
        stats = call_api("/stats")
        if stats:
            st.metric("数据库案例数", stats.get("total_cases", 0))
            st.metric("理论知识点数", stats.get("total_theories", 0))
    else:
        st.error("后端服务离线")


if page == "案例分析":
    st.subheader("案例输入")
    input_method = st.radio("选择输入方式", ["PDF文件上传", "文本输入"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        case_name = st.text_input("案例名称 *")
        author = st.text_input("作者", placeholder="可选")
        subject = st.text_input("学科领域", placeholder="如：市场营销、战略管理等")
    with col2:
        industry = st.text_input("行业", placeholder="如：制造业、金融等")
        keywords = st.text_input("关键词", placeholder="多个用逗号分隔")
        theories_input = st.text_input("主要理论 (可选)", placeholder="留空则自动识别；多个用逗号分隔")

    if input_method == "PDF文件上传":
        uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
        if st.button("开始分析", type="primary", disabled=not (case_name and uploaded_file)):
            with st.spinner("正在分析..."):
                data = {"name": case_name}
                if author: data["author"] = author
                if subject: data["subject"] = subject
                if industry: data["industry"] = industry
                if keywords: data["keywords"] = keywords
                if theories_input:
                    data["theories"] = theories_input
                    data["primary_theories"] = theories_input  # 主要理论
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                result = call_api("/analyze/upload", method="POST", data=data, files=files)
                if result:
                    st.session_state.analysis_result = result
    else:
        case_text = st.text_area("案例文本 *", height=300)
        if st.button("开始分析", type="primary", disabled=not (case_name and case_text)):
            with st.spinner("正在分析..."):
                data = {"name": case_name, "text": case_text}
                if author: data["author"] = author
                if subject: data["subject"] = subject
                if industry: data["industry"] = industry
                if keywords: data["keywords"] = keywords
                if theories_input:
                    theory_list = [t.strip() for t in theories_input.split(',') if t.strip()]
                    data["theories"] = theory_list
                    data["primary_theories"] = theory_list  # 主要理论
                result = call_api("/analyze/text", method="POST", data=data)
                if result:
                    st.session_state.analysis_result = result

    if hasattr(st.session_state, 'analysis_result'):
        st.markdown("---")
        st.subheader("分析结果")
        result = st.session_state.analysis_result

        # 创新度指标（新分组文案）
        st.markdown("### 创新度评估")
        innovation = result.get("innovation_score", {})
        score = innovation.get("innovation_score", 0)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("创新度总分", f"{score:.1f}", help="基于理论频次合成 (0-100)")
        with c2:
            st.metric("新颖理论(≤2)", f"{len(innovation.get('novel_theories', []))} 项")
        with c3:
            st.metric("常见理论(3-4)", f"{len(innovation.get('common_theories', []))} 项")
        with c4:
            st.metric("经典理论(≥5)", f"{len(innovation.get('high_frequency_theories', []))} 项")

        # 理论匹配
        st.markdown("### 理论匹配结果")
        theories = result.get("identified_theories", [])
        primary_theories = result.get("primary_theories", []) or []
        exact_matches = result.get("exact_matches", {})

        # 分离主要理论和其他理论
        if primary_theories:
            # 有主要理论时，分两部分显示
            st.markdown("#### 📌 主要理论查重")
            primary_found = False
            for t in [t for t in theories if t in primary_theories and t in exact_matches]:
                primary_found = True
                info = exact_matches[t]
                cases = info.get('cases', [])
                with st.expander(f"⭐ {t} - 使用 {info.get('match_count', 0)} 次（{info.get('frequency_rank','未知')}）", expanded=True):
                    if cases:
                        df = pd.DataFrame([
                            {
                                "案例名称": c.get('name', 'N/A'),
                                "案例编号": c.get('code', 'N/A'),
                                "年份": c.get('year', 'N/A'),
                                "学科": c.get('subject', 'N/A'),
                                "行业": c.get('industry', 'N/A'),
                            } for c in cases
                        ])
                        st.dataframe(df, use_container_width=True, hide_index=True)
            if not primary_found:
                st.info("未找到主要理论的匹配结果")

            st.markdown("#### 📚 其他理论查重")
            other_theories = [t for t in theories if t not in primary_theories and t in exact_matches]
            if other_theories:
                for t in other_theories:
                    info = exact_matches[t]
                    cases = info.get('cases', [])
                    with st.expander(f"{t} - 使用 {info.get('match_count', 0)} 次（{info.get('frequency_rank','未知')}）"):
                        if cases:
                            df = pd.DataFrame([
                                {
                                    "案例名称": c.get('name', 'N/A'),
                                    "案例编号": c.get('code', 'N/A'),
                                    "年份": c.get('year', 'N/A'),
                                    "学科": c.get('subject', 'N/A'),
                                    "行业": c.get('industry', 'N/A'),
                                } for c in cases
                            ])
                            st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("未找到其他理论的匹配结果")
        else:
            # 没有主要理论时，按原样显示
            if exact_matches:
                for t in [t for t in theories if t in exact_matches]:
                    info = exact_matches[t]
                    cases = info.get('cases', [])
                    with st.expander(f"{t} - 使用 {info.get('match_count', 0)} 次（{info.get('frequency_rank','未知')}）"):
                        if cases:
                            df = pd.DataFrame([
                                {
                                    "案例名称": c.get('name', 'N/A'),
                                    "案例编号": c.get('code', 'N/A'),
                                    "年份": c.get('year', 'N/A'),
                                    "学科": c.get('subject', 'N/A'),
                                    "行业": c.get('industry', 'N/A'),
                                } for c in cases
                            ])
                            st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("未找到匹配结果")

        # 相似案例排名
        st.markdown("### 相似案例排名")
        similar_cases = result.get("similar_cases", [])
        if similar_cases:
            rows = []
            for i, c in enumerate(similar_cases, 1):
                meta = c.get('metadata', {})
                scs = c.get('scores', {})
                rows.append({
                    "排名": i,
                    "案例名称": meta.get('name', 'N/A'),
                    "年份": meta.get('year', 'N/A'),
                    "综合相似度": f"{scs.get('final_score', 0):.3f}",
                    "语义相似度": f"{scs.get('semantic_similarity', 0):.3f}",
                    "学科": meta.get('subject', 'N/A'),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("未找到相似案例")


elif page == "理论查询":
    st.subheader("理论知识点查询（支持同义合并）")
    theories = call_api("/theories/") or []
    q = st.text_input("输入理论关键词进行搜索", placeholder="如 SWOT / 蓝海 / 波特五力 ...")
    if q:
        # 直接调用对应 API，返回即为标准化后的合并结果
        res = call_api(f"/theories/{q}/cases")
        if res:
            st.write(f"标准化名称：{res.get('theory_name')}")
            st.write(f"使用次数：{res.get('usage_count')}  ·  频次等级：{res.get('frequency_rank')}")
            cases = res.get('cases', [])
            if cases:
                st.dataframe(pd.DataFrame(cases), use_container_width=True)
    else:
        st.info("输入关键词后回车查询")


elif page == "案例检索":
    st.subheader("案例检索")
    col1, col2 = st.columns(2)
    with col1:
        kw = st.text_input("关键词")
        subj = st.text_input("学科")
    with col2:
        ind = st.text_input("行业")
        year = st.text_input("年份")
    limit = st.slider("返回数量", 10, 100, 50, 10)
    if st.button("开始检索", type="primary"):
        params = {"limit": limit}
        if kw: params['keyword'] = kw
        if subj: params['subject'] = subj
        if ind: params['industry'] = ind
        if year: params['year'] = year
        res = call_api("/cases/search", method="GET", data=params)
        if res:
            st.dataframe(pd.DataFrame(res.get('cases', [])), use_container_width=True, hide_index=True)
