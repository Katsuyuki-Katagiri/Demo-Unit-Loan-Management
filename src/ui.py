import streamlit as st

def render_header(title: str, icon_name: str = None):
    """
    Renders a consistent, stylish header with an optional Material Icon.
    """
    if icon_name:
        st.markdown(f"""
            <h1>
                <span class="material-symbols-rounded header-icon">{icon_name}</span>
                {title}
            </h1>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
