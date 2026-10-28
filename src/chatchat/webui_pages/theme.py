"""Q2A 文档站风格的 WebUI 主题。

整体视觉参考 https://docs.question2answer.org/ ：
  * 顶部橙色导航条 + 底部波浪
  * 左侧白色文档目录栏
  * 右侧白色内容卡片（1px 描边 + 轻阴影）
  * 橙色调 #ff773d / #ff6b2b，正文 #424242，底色 #f8f8f8

Streamlit 没有官方的主题插槽，这里通过两层实现：
  1. 注入 ``assets/q2a_theme.css`` 覆盖 Streamlit 生成的 DOM（data-testid 选择器）
  2. 用 ``st.markdown(unsafe_allow_html=True)`` 渲染固定定位的导航条、面包屑和页脚

对外只有 4 个函数：inject_theme / render_header / render_brand+nav / render_footer。
"""

from pathlib import Path

import streamlit as st

APP_NAME = "智能聊天"
APP_SUBTITLE = "AI Chat · Knowledge Base Q&A"
GITHUB_URL = "https://github.com/chatchat-space/Langchain-Chatchat"

_ASSETS_DIR = Path(__file__).parent / "assets"
_CSS_FILE = _ASSETS_DIR / "q2a_theme.css"

# Q2A 官方 wave-combo.svg 的三条路径，直接内联，避免外链依赖
_WAVE_SVG = """
<svg class="q2a-wave" viewBox="0 0 1440 170" preserveAspectRatio="none"
     xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path fill="#ff773d" fill-opacity="1"
        d="M0,128L60,117.3C120,107,240,85,360,74.7C480,64,600,64,720,69.3C840,75,960,85,1080,85.3C1200,85,1320,75,1380,69.3L1440,64L1440,0L1380,0C1320,0,1200,0,1080,0C960,0,840,0,720,0C600,0,480,0,360,0C240,0,120,0,60,0L0,0Z"/>
  <path fill="#ff773d" fill-opacity="0.55"
        d="M0,160L48,154.7C96,149,192,139,288,128C384,117,480,107,576,106.7C672,107,768,117,864,112C960,107,1056,85,1152,85.3C1248,85,1344,107,1392,117.3L1440,128L1440,0L1392,0C1344,0,1248,0,1152,0C1056,0,960,0,864,0C768,0,672,0,576,0C480,0,384,0,288,0C192,0,96,0,48,0L0,0Z"/>
  <path fill="#ff773d" fill-opacity="0.45"
        d="M0,64L60,85.3C120,107,240,149,360,144C480,139,600,85,720,74.7C840,64,960,96,1080,112C1200,128,1320,128,1380,128L1440,128L1440,0L1380,0C1320,0,1200,0,1080,0C960,0,840,0,720,0C600,0,480,0,360,0C240,0,120,0,60,0L0,0Z"/>
</svg>
"""


def load_css() -> str:
    """读取主题样式。开发时可直接改 css 文件，刷新页面即可生效。"""
    try:
        return _CSS_FILE.read_text(encoding="utf-8")
    except OSError as e:  # 样式文件丢失不应该让整个页面起不来
        st.warning(f"主题样式加载失败：{e}")
        return ""


def inject_theme() -> None:
    """注入全局样式，必须在 set_page_config 之后、其他 st 组件之前调用。"""
    st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)


def render_header(version: str = "", api_docs_url: str = "") -> None:
    """渲染固定顶部的橙色导航条（含 Q2A 波浪底边）。"""
    docs_link = (
        f'<a href="{api_docs_url}" target="_blank" rel="noopener">API 文档</a>'
        if api_docs_url
        else '<span class="q2a-nav-item">API 文档</span>'
    )
    st.markdown(
        f"""
<header class="q2a-header">
  <a class="q2a-brand" href="{GITHUB_URL}" target="_blank" rel="noopener">
    <span class="q2a-brand-badge">智</span>
    <span>{APP_NAME}</span>
  </a>
  <nav class="q2a-nav">
    <span class="q2a-nav-item is-active">对话</span>
    <span class="q2a-nav-item">知识库</span>
    {docs_link}
    <a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>
  </nav>
  <span class="q2a-version">v{version}</span>
  {_WAVE_SVG}
</header>
""",
        unsafe_allow_html=True,
    )


def render_brand(version: str = "") -> None:
    """侧栏顶部的品牌区 + 「导航」小节标题。"""
    st.markdown(
        f"""
<div class="q2a-side-brand">
  <div class="q2a-side-title">{APP_NAME}</div>
  <div class="q2a-side-sub">{APP_SUBTITLE}</div>
</div>
<div class="q2a-side-section">导航</div>
""",
        unsafe_allow_html=True,
    )


def nav(options: list[str], key: str = "selected_page") -> str:
    """把 Streamlit 原生 radio 渲染成文档目录样式的导航。

    用 radio 而不是第三方菜单组件，是因为 streamlit-antd-components 的 menu
    跑在 iframe 里，外部 CSS 无法进入，风格会跟主题割裂。
    """
    return st.radio(
        "导航",
        options,
        key=key,
        label_visibility="collapsed",
    )


def sidebar_divider() -> None:
    st.markdown('<div class="q2a-side-sep"></div>', unsafe_allow_html=True)


def sidebar_footnote(version: str = "") -> None:
    st.markdown(
        f"""
<div class="q2a-side-foot">
  Langchain-Chatchat <b>v{version}</b><br/>
  检索增强问答 · FAISS + BM25 + DeepSeek
</div>
""",
        unsafe_allow_html=True,
    )


def render_breadcrumb(page_name: str, section: str = "文档") -> None:
    """内容卡片顶部的面包屑，和 Q2A 的 docs 内页一致。"""
    st.markdown(
        f"""
<div class="q2a-crumbs">
  <a href="#" onclick="return false;">主页</a>
  <span class="q2a-crumb-sep">›</span>
  <a href="#" onclick="return false;">{section}</a>
  <span class="q2a-crumb-sep">›</span>
  <span class="q2a-crumb-current">{page_name}</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        f"""
<footer class="q2a-footer">
  <span>{APP_NAME} · 基于 Langchain-Chatchat 构建的本地知识库问答系统</span>
  <span>
    <a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>
    <a href="https://github.com/chatchat-space/Langchain-Chatchat/issues" target="_blank" rel="noopener">反馈问题</a>
  </span>
</footer>
""",
        unsafe_allow_html=True,
    )
