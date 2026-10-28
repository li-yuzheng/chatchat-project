import sys

import streamlit as st

from chatchat import __version__
from chatchat.server.utils import api_address
from chatchat.webui_pages import theme
from chatchat.webui_pages.dialogue.dialogue import dialogue_page
from chatchat.webui_pages.kb_chat import kb_chat
from chatchat.webui_pages.knowledge_base.knowledge_base import knowledge_base_page
from chatchat.webui_pages.utils import *

api = ApiRequest(base_url=api_address())

# 页面名称 -> 渲染函数。侧栏导航由这个字典直接生成，顺序即展示顺序
PAGES = {
    "智能聊天": "dialogue",
    "RAG 知识问答": "rag",
    "知识库管理": "kb",
}


def run_webui() -> None:
    is_lite = "lite" in sys.argv  # TODO: remove lite mode

    st.set_page_config(
        page_title=theme.APP_NAME,
        page_icon=get_img_base64("chatchat_icon_blue_square_v2.png"),
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": theme.GITHUB_URL,
            "Report a bug": f"{theme.GITHUB_URL}/issues",
            "About": f"{theme.APP_NAME} v{__version__} · 基于 Langchain-Chatchat 的本地知识库问答",
        },
        layout="centered",
    )

    # Q2A 文档站风格主题 + 顶部固定导航条
    theme.inject_theme()
    theme.render_header(
        version=__version__,
        api_docs_url=f"{api_address()}/docs",
    )

    with st.sidebar:
        theme.render_brand(version=__version__)
        selected_page = theme.nav(list(PAGES))
        theme.sidebar_divider()

    # 面包屑（Q2A 文档内页的「主页 › 文档 › 当前页」）按需求去掉，
    # 需要时打开下面这行即可恢复：theme.render_breadcrumb(selected_page)

    page = PAGES.get(selected_page, "dialogue")
    if page == "kb":
        knowledge_base_page(api=api, is_lite=is_lite)
    elif page == "rag":
        kb_chat(api=api)
    else:
        dialogue_page(api=api, is_lite=is_lite)

    theme.render_footer()


if __name__ == "__main__":
    run_webui()
