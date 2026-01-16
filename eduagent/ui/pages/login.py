from __future__ import annotations

import re
import time

import streamlit as st

from eduagent.ui.api_client import EduAgentAPIClient


def _calculate_password_strength(password: str) -> tuple[str, str, str]:
    """Calculate password strength and return label, color and bar.

    Args:
        password: The password to evaluate

    Returns:
        Tuple of (strength_label, strength_color, bar_character)
    """
    if not password:
        return "", "gray", " "

    score = 0
    # Length check
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1

    # Complexity checks
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1

    # Map score to strength
    if score <= 2:
        return "弱", "red", "▓▓░░░"
    elif score <= 4:
        return "中等", "orange", "▓▓▓▓░"
    else:
        return "强", "green", "▓▓▓▓▓"


def _render_left_column() -> None:
    """Render the beautiful left column with branding and features using pure Streamlit."""
    # Apply gradient background using Streamlit's container
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"]:has(> div[data-testid="column"]) {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Title
    st.title("EduAgent")

    # Subtitle
    st.markdown("*智能教育平台，赋能个性化学习体验*")
    st.markdown("---")

    # Features using st.info for better visual
    st.markdown("### 核心功能")

    # Feature 1
    st.markdown("📚 **智能文档管理**")
    st.caption("支持多种格式文档上传与解析")

    st.markdown("---")

    # Feature 2
    st.markdown("🔍 **高级检索引擎**")
    st.caption("稀疏、密集、混合多种检索模式")

    st.markdown("---")

    # Feature 3
    st.markdown("🤖 **多智能体协作**")
    st.caption("自动路由、对话、出题多种模式")

    st.markdown("---")

    # Feature 4
    st.markdown("📊 **数据可视化分析**")
    st.caption("实时监控学习进度与效果")

    st.markdown("---")

    # Footer
    st.caption("© 2025 EduAgent. All rights reserved.")


def _render_right_column(client: EduAgentAPIClient) -> None:
    """Render the login form in the right column.

    Args:
        client: The API client for backend communication
    """
    # Initialize show password state
    if "show_password" not in st.session_state:
        st.session_state.show_password = False

    # Login form header
    st.subheader("欢迎回来")
    st.caption("请登录您的账户")

    # Role selection
    role = st.selectbox(
        label="选择角色",
        options=["教师", "学生"],
        index=0,
        label_visibility="visible",
        help="选择您的身份以获得个性化的学习体验",
    )

    # Show/hide password checkbox (using checkbox instead of button for form compatibility)
    show_password = st.checkbox("显示密码", value=False, key="show_password_checkbox")
    st.session_state.show_password = show_password

    # Login form
    with st.form("login_form", clear_on_submit=False):
        # Username field
        username = st.text_input(
            label="用户名",
            placeholder="请输入用户名",
            max_chars=50,
            help="至少3个字符",
        )

        # Password field
        password_input_type = "default" if st.session_state.show_password else "password"
        password = st.text_input(
            label="密码",
            placeholder="请输入密码",
            type=password_input_type,
            max_chars=100,
            help="至少6个字符",
            key="password_input",
        )

        # Password strength indicator using pure Streamlit
        if password:
            strength_label, color_name, bar = _calculate_password_strength(password)
            color_emoji = {"red": "🔴", "orange": "🟠", "green": "🟢", "gray": "⚪"}[color_name]

            # Strength display
            col1, col2 = st.columns([1, 4])
            with col1:
                st.caption("密码强度")
            with col2:
                st.markdown(f"{color_emoji} **{strength_label}**")

            # Strength bar
            st.text(bar)

        # Remember me checkbox
        remember_me = st.checkbox("记住我")

        st.markdown("*忘记密码？*")

        # Login button
        submit_button = st.form_submit_button(
            label="登录",
            use_container_width=True,
            type="primary",
        )

        # Handle form submission
        if submit_button:
            # Validate inputs
            if not username:
                st.error("请输入用户名")
            elif len(username) < 3:
                st.error("用户名至少需要3个字符")
            elif not password:
                st.error("请输入密码")
            elif len(password) < 6:
                st.error("密码至少需要6个字符")
            else:
                # Fake login - in real app, would call API
                with st.spinner("正在登录..."):
                    # Simulate API call
                    time.sleep(1)

                    # Set login state
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = role

                    st.success(f"登录成功！欢迎回来，{username}（{role}）")
                    time.sleep(0.5)
                    st.rerun()

    # Divider
    st.markdown("---")
    st.markdown("*或使用第三方登录*")
    st.markdown("---")

    # Social login buttons (fake)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(
            "🔐 微信",
            use_container_width=True,
            key="wechat_login",
            help="使用微信登录",
        ):
            st.info("微信登录功能开发中...")
    with col2:
        if st.button(
            "📧 邮箱",
            use_container_width=True,
            key="email_login",
            help="使用邮箱登录",
        ):
            st.info("邮箱登录功能开发中...")
    with col3:
        if st.button(
            "📱 手机",
            use_container_width=True,
            key="phone_login",
            help="使用手机号登录",
        ):
            st.info("手机登录功能开发中...")

    # Sign up prompt
    st.markdown("---")
    st.markdown("*还没有账户？立即注册*")

    # Forgot password expander
    with st.expander("🔑 忘记密码？", expanded=False):
        st.markdown("##### 重置密码")
        st.caption("请输入您的邮箱地址，我们将发送密码重置链接。")

        reset_email = st.text_input(
            label="邮箱地址",
            placeholder="请输入注册邮箱",
            key="reset_email",
        )

        if st.button("发送重置链接", key="send_reset", use_container_width=True):
            if not reset_email:
                st.warning("请输入邮箱地址")
            elif "@" not in reset_email:
                st.warning("请输入有效的邮箱地址")
            else:
                with st.spinner("正在发送..."):
                    time.sleep(0.5)
                    st.success(f"密码重置链接已发送至 {reset_email}")
                    st.info("💡 演示模式：实际不会发送邮件")

    # Registration expander
    with st.expander("📝 注册新账户", expanded=False):
        st.markdown("##### 创建新账户")

        with st.form("register_form", clear_on_submit=True):
            # Username
            reg_username = st.text_input(
                label="用户名",
                placeholder="请输入用户名（至少3个字符）",
                key="reg_username",
            )

            # Email
            reg_email = st.text_input(
                label="邮箱地址",
                placeholder="请输入邮箱地址",
                key="reg_email",
            )

            # Password
            reg_password = st.text_input(
                label="密码",
                placeholder="请输入密码（至少6个字符）",
                type="password",
                key="reg_password",
            )

            # Confirm password
            reg_confirm = st.text_input(
                label="确认密码",
                placeholder="请再次输入密码",
                type="password",
                key="reg_confirm",
            )

            # Role selection
            reg_role = st.selectbox(
                label="选择角色",
                options=["教师", "学生"],
                index=0,
                key="reg_role",
            )

            # Terms checkbox
            agree_terms = st.checkbox("我已阅读并同意《用户协议》和《隐私政策》")

            # Submit button
            if st.form_submit_button("注册", use_container_width=True, type="primary"):
                # Validation
                if not reg_username:
                    st.error("请输入用户名")
                elif len(reg_username) < 3:
                    st.error("用户名至少需要3个字符")
                elif not reg_email or "@" not in reg_email:
                    st.error("请输入有效的邮箱地址")
                elif not reg_password:
                    st.error("请输入密码")
                elif len(reg_password) < 6:
                    st.error("密码至少需要6个字符")
                elif reg_password != reg_confirm:
                    st.error("两次输入的密码不一致")
                elif not agree_terms:
                    st.error("请同意用户协议和隐私政策")
                else:
                    with st.spinner("正在注册..."):
                        time.sleep(1)
                        st.success(f"注册成功！欢迎加入，{reg_username}！")
                        st.info("💡 演示模式：实际不会创建账户")

    # Demo account hint
    st.info(
        """
        💡 **演示账户**
        - 用户名: `demo` 或任意用户名
        - 密码: 任意密码（至少6位）
        - 角色: 选择教师或学生
        """
    )

    # Show current login status if logged in
    if st.session_state.get("logged_in"):
        st.success(
            f"""
            ✅ **当前已登录**
            - 用户名: {st.session_state.get('username', 'Unknown')}
            - 角色: {st.session_state.get('user_role', 'Unknown')}
            """
        )
        # Logout button
        if st.button("退出登录", use_container_width=True, key="logout", type="secondary"):
            # Clear login state
            for key in ["logged_in", "username", "user_role"]:
                st.session_state.pop(key, None)
            st.success("已退出登录")
            time.sleep(0.5)
            st.rerun()


def render(client: EduAgentAPIClient) -> None:
    """Render the login page with a two-column layout.

    Args:
        client: The API client for backend communication
    """
    # Page title
    st.title("登录 / Login")

    # Create two columns for the login page
    col_left, col_right = st.columns([1, 1])

    with col_left:
        _render_left_column()

    with col_right:
        _render_right_column(client)
