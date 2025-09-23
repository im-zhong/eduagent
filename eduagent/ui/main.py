"""
Main UI Entry Point for EduAgent System
Provides role-based access to teacher and student interfaces
"""

import streamlit as st

from eduagent.defs import defs
from eduagent.ui.api_client import EduAgentAPIClient
from eduagent.ui.student_interface import StudentInterface
from eduagent.ui.teacher_interface import TeacherInterface


def main() -> None:
    """Main entry point for the EduAgent UI"""

    # Initialize API client
    api_client = EduAgentAPIClient()

    # Role selection page
    st.set_page_config(
        page_title="EduAgent - Educational AI Platform",
        page_icon=defs.ui.PAGE_ICON,
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    # Welcome page with role selection
    st.title("📚 Welcome to EduAgent")
    st.markdown("""
    ### AI-Powered Educational Question Generation System

    EduAgent helps educators create intelligent questions and provides students
    with personalized learning experiences powered by AI.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👨‍🏫 Teacher Portal")
        st.markdown("""
        - Upload and analyze textbooks
        - Generate educational questions
        - Monitor student progress
        - Create practice exercises
        """)
        if st.button("Enter as Teacher", width='stretch'):
            st.session_state.role = "teacher"
            st.rerun()

    with col2:
        st.subheader("👨‍🎓 Student Portal")
        st.markdown("""
        - Practice with AI-generated questions
        - Track learning progress
        - Get personalized feedback
        - Ask questions to AI tutor
        """)
        if st.button("Enter as Student", width='stretch'):
            st.session_state.role = "student"
            st.rerun()

    # System information
    st.markdown("---")
    st.subheader("🔧 System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Check API Health"):
            with st.spinner("Checking system health..."):
                result = api_client.health_check()
                if "error" not in result:
                    st.success("✅ API is healthy!")
                    st.json(result)
                else:
                    st.error(f"API health check failed: {result['error']}")

    with col2:
        st.write("**Current API URL:**")
        st.code(api_client.base_url)

    with col3:
        st.write("**System Version:**")
        st.code("EduAgent v1.0.0")


def run_interface() -> None:
    """Run the appropriate interface based on user role"""

    # Initialize API client
    api_client = EduAgentAPIClient()

    # Check if role is selected
    if "role" not in st.session_state:
        main()
        return

    # Run the appropriate interface
    if st.session_state.role == "teacher":
        teacher_ui = TeacherInterface(api_client)
        teacher_ui.run()
    elif st.session_state.role == "student":
        student_ui = StudentInterface(api_client)
        student_ui.run()

    # Add logout functionality
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        # Clear session state and rerun
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


if __name__ == "__main__":
    run_interface()
