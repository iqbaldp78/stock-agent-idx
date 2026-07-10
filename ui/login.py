import streamlit as st
import time
from services.auth import authenticate_user

import extra_streamlit_components as stx
import uuid

def init_cookie_manager(key="init"):
    # CookieManager injects an invisible widget, so we must instantiate it
    # every time the script reruns without caching it. 
    # extra_streamlit_components handles the deduplication internally.
    return stx.CookieManager(key=key)

def render_login_page(get_db_conn_func):
    """Renders the login page and handles authentication."""
    
    # Custom CSS for the login page specifically
    st.markdown("""
    <style>
    .login-title-container {
        text-align: center;
        margin-bottom: 30px;
        margin-top: 50px;
    }
    .login-title {
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 10px;
        background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .login-tagline {
        font-size: 16px;
        color: #94a3b8;
        font-weight: 300;
    }
    /* Hide sidebar when not authenticated */
    [data-testid="collapsedControl"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('''
            <div class="login-title-container">
                <div class="login-title">🤖 Stock Agent IDX</div>
                <div class="login-tagline" style="margin-bottom: 5px;">AI-Powered Indonesian Stock Analysis & Trading Agent</div>
                <div class="login-tagline" style="font-size: 14px; opacity: 0.8;">Your trading Mechanism has been Upgrade</div>
            </div>
        ''', unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate_user(username, password, get_db_conn_func)
                    if user:
                        st.success(f"Welcome back, {username}!")
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        
                        # Save to cookie for persistence
                        cookie_manager = init_cookie_manager(key="login_cookie_mgr")
                        cookie_manager.set("auth_token", username, max_age=86400 * 7) # 7 days
                        
                        time.sleep(1) # Let the user see the success message
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")
