"""
Teacher Interface for EduAgent System
Provides tools for textbook upload, knowledge extraction, question generation, and analytics
"""


import pandas as pd
import plotly.express as px
import streamlit as st

from eduagent.defs import defs


class TeacherInterface:
    """Teacher interface for managing educational content and analytics"""

    def __init__(self, api_client) -> None:
        self.api_client = api_client
        self.setup_page_config()

    def setup_page_config(self) -> None:
        """Configure Streamlit page settings"""
        st.set_page_config(
            page_title=defs.ui.TEACHER_DASHBOARD_TITLE,
            page_icon=defs.ui.PAGE_ICON,
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def render_sidebar(self) -> str:
        """Render sidebar navigation"""
        st.sidebar.title("📚 EduAgent Teacher")
        st.sidebar.markdown("---")

        # Navigation using UI definitions
        selected_nav = st.sidebar.radio("Navigation", defs.ui.TEACHER_NAV_OPTIONS)
        return selected_nav

    def render_dashboard(self) -> None:
        """Render main dashboard"""
        st.title("🏠 Teacher Dashboard")

        # Quick stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Active Classes", "3")
        with col2:
            st.metric("Total Students", "75")
        with col3:
            st.metric("Generated Questions", "156")
        with col4:
            st.metric("Avg. Accuracy", "78%")

        st.markdown("---")

        # Recent activity
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📈 Recent Performance")
            # Mock performance data
            performance_data = pd.DataFrame({
                "Date": pd.date_range("2024-01-01", periods=7, freq="D"),
                "Accuracy": [75, 78, 82, 79, 81, 85, 83]
            })
            fig = px.line(performance_data, x="Date", y="Accuracy",
                         title="Class Performance Trend")
            st.plotly_chart(fig, width='stretch')

        with col2:
            st.subheader("🔔 Recent Activity")
            activities = [
                "New textbook uploaded: Math Grade 8",
                "Generated 15 questions for Algebra",
                "Student performance report generated",
                "Class analytics updated"
            ]
            for activity in activities:
                st.info(f"• {activity}")

    def render_textbook_management(self) -> None:
        """Render textbook upload and management interface"""
        st.title("📖 Textbook Management")

        tab1, tab2, tab3 = st.tabs(["Upload Textbook", "Knowledge Graph", "Extraction Status"])

        with tab1:
            st.subheader("Upload New Textbook")

            with st.form("textbook_upload_form"):
                uploaded_file = st.file_uploader(
                    "Choose textbook file",
                    type=["pdf", "docx", "jpg", "png"],
                    help="Supported formats: PDF, DOCX, JPG, PNG"
                )

                col1, col2 = st.columns(2)
                with col1:
                    subject = st.selectbox("Subject", defs.ui.SUBJECTS)
                with col2:
                    grade_level = st.selectbox("Grade Level", defs.ui.GRADE_LEVELS)

                if st.form_submit_button("Upload & Extract Knowledge"):
                    if uploaded_file is not None:
                        with st.spinner("Uploading and extracting knowledge..."):
                            # Save file and trigger extraction
                            result = self.api_client.upload_textbook(
                                uploaded_file.name, subject, grade_level
                            )
                            if "error" not in result:
                                st.success("Textbook uploaded successfully!")
                                st.info(f"Extraction ID: {result.get('extraction_id', 'N/A')}")
                            else:
                                st.error(f"Upload failed: {result['error']}")

        with tab2:
            st.subheader("Knowledge Graph Viewer")
            st.info("Visualize the extracted knowledge structure from textbooks")

            # Mock knowledge graph visualization
            if st.button("Load Knowledge Graph"):
                with st.spinner("Loading knowledge graph..."):
                    # Mock data
                    knowledge_points = [
                        {"id": "kp1", "name": "Algebra", "connections": 5},
                        {"id": "kp2", "name": "Geometry", "connections": 3},
                        {"id": "kp3", "name": "Calculus", "connections": 4}
                    ]

                    df = pd.DataFrame(knowledge_points)
                    st.dataframe(df)

                    # Simple network visualization
                    st.write("**Knowledge Connections**")
                    for kp in knowledge_points:
                        st.write(f"📚 {kp['name']} - {kp['connections']} connections")

        with tab3:
            st.subheader("Extraction Status")
            extraction_id = st.text_input("Enter Extraction ID")

            if st.button("Check Status") and extraction_id:
                with st.spinner("Checking extraction status..."):
                    result = self.api_client.get_extraction_status(extraction_id)
                    if "error" not in result:
                        status = result.get("status", "unknown")
                        if status == "completed":
                            st.success("✅ Extraction completed")
                            st.json(result)
                        elif status == "processing":
                            st.warning("🔄 Extraction in progress...")
                        else:
                            st.info(f"Status: {status}")
                    else:
                        st.error(f"Error: {result['error']}")

    def render_question_generation(self) -> None:
        """Render question generation interface"""
        st.title("❓ Question Generation")

        tab1, tab2, tab3 = st.tabs(["Generate Questions", "Difficulty Control", "Distractor Generation"])

        with tab1:
            st.subheader("Generate Educational Questions")

            with st.form("question_generation_form"):
                col1, col2 = st.columns(2)

                with col1:
                    knowledge_points = st.multiselect(
                        "Select Knowledge Points",
                        ["Algebra", "Geometry", "Calculus", "Statistics", "Trigonometry"],
                        help="Select the topics to base questions on"
                    )

                    question_type = st.selectbox("Question Type", defs.ui.QUESTION_TYPES)

                with col2:
                    difficulty = st.select_slider("Difficulty Level", options=defs.ui.DIFFICULTY_LEVELS)
                    num_questions = st.slider("Number of Questions", min_value=1, max_value=20, value=5)

                _cognitive_level = st.selectbox("Cognitive Level", defs.ui.COGNITIVE_LEVELS)

                if st.form_submit_button("Generate Questions"):
                    if knowledge_points:
                        with st.spinner("Generating questions..."):
                            result = self.api_client.generate_questions(
                                knowledge_points, question_type.lower().replace(" ", "_"),
                                difficulty.lower(), num_questions
                            )

                            if "error" not in result:
                                st.success(f"✅ Generated {len(result.get('questions', []))} questions!")

                                for i, question in enumerate(result.get("questions", []), 1):
                                    with st.expander(f"Question {i}: {question.get('question_text', 'N/A')}"):
                                        st.write(f"**Type:** {question.get('question_type', 'N/A')}")
                                        st.write(f"**Difficulty:** {question.get('difficulty', 'N/A')}")
                                        st.write(f"**Cognitive Level:** {question.get('cognitive_level', 'N/A')}")

                                        if question.get("options"):
                                            st.write("**Options:**")
                                            for opt in question["options"]:
                                                marker = "✅" if opt.get("is_correct") else "❌"
                                                st.write(f"{marker} {opt.get('text', 'N/A')}")

                                        if question.get("explanation"):
                                            st.write(f"**Explanation:** {question['explanation']}")
                            else:
                                st.error(f"Generation failed: {result['error']}")
                    else:
                        st.warning("Please select at least one knowledge point")

        with tab2:
            st.subheader("Question Difficulty Control")

            question_text = st.text_area(
                "Enter Question Text",
                placeholder="Enter the question you want to adjust..."
            )

            target_difficulty = st.slider(
                "Target Difficulty",
                min_value=0.1, max_value=1.0, value=0.5, step=0.1
            )

            if st.button("Adjust Difficulty") and question_text:
                with st.spinner("Adjusting question difficulty..."):
                    result = self.api_client.control_question_difficulty(
                        question_text, target_difficulty
                    )

                    if "error" not in result:
                        st.success("✅ Difficulty adjusted successfully!")
                        st.write("**Original Question:**")
                        st.info(question_text)
                        st.write("**Adjusted Question:**")
                        st.success(result.get("adjusted_question", "N/A"))

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Difficulty Score", f"{result.get('difficulty_score', 0):.2f}")
                        with col2:
                            st.metric("Cognitive Complexity", f"{result.get('cognitive_complexity', 0):.2f}")
                        with col3:
                            st.metric("Step Count", result.get("step_count", 0))
                    else:
                        st.error(f"Adjustment failed: {result['error']}")

        with tab3:
            st.subheader("Distractor Generation")

            question_text = st.text_area(
                "Enter Multiple Choice Question",
                placeholder="Enter the question stem...",
                key="distractor_question"
            )

            knowledge_point = st.selectbox(
                "Related Knowledge Point",
                ["Algebra", "Geometry", "Calculus", "Statistics", "Trigonometry"]
            )

            if st.button("Generate Distractors") and question_text:
                with st.spinner("Generating cognitively appropriate distractors..."):
                    result = self.api_client.generate_distractors(question_text, knowledge_point)

                    if "error" not in result:
                        st.success("✅ Distractors generated successfully!")
                        distractors = result.get("distractors", [])

                        st.write("**Generated Distractors:**")
                        for i, distractor in enumerate(distractors, 1):
                            with st.expander(f"Distractor {i}: {distractor.get('text', 'N/A')}"):
                                st.write(f"**Mistake Pattern:** {distractor.get('mistake_pattern', 'N/A')}")
                                st.write("**Educational Value:** High")
                    else:
                        st.error(f"Generation failed: {result['error']}")

    def render_analytics(self) -> None:
        """Render analytics and reporting interface"""
        st.title("📊 Analytics & Reports")

        tab1, tab2, tab3 = st.tabs(["Student Performance", "Class Analytics", "Mistake Analysis"])

        with tab1:
            st.subheader("Individual Student Performance")

            student_id = st.text_input("Student ID")
            time_period = st.selectbox("Time Period", defs.ui.TIME_PERIODS)

            if st.button("Get Performance Report") and student_id:
                with st.spinner("Generating performance report..."):
                    result = self.api_client.get_performance_analytics(student_id, time_period)

                    if "error" not in result:
                        st.success("✅ Performance report generated!")

                        # Display key metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Overall Accuracy", f"{result.get('overall_accuracy', 0)*100:.1f}%")
                        with col2:
                            st.metric("Total Attempts", result.get("total_attempts", 0))
                        with col3:
                            st.metric("Avg. Time/Question", f"{result.get('average_time_per_question', 0):.1f}s")

                        # Knowledge point breakdown
                        st.subheader("Knowledge Point Analysis")
                        kp_data = result.get("knowledge_point_analytics", [])
                        if kp_data:
                            df = pd.DataFrame(kp_data)
                            st.dataframe(df)

                        # Weak areas
                        weak_areas = result.get("weak_areas", [])
                        if weak_areas:
                            st.subheader("Weak Areas")
                            for area in weak_areas:
                                st.warning(f"• {area}")
                    else:
                        st.error(f"Analytics failed: {result['error']}")

        with tab2:
            st.subheader("Class Analytics")

            class_id = st.text_input("Class ID")
            time_period = st.selectbox(
                "Time Period for Class",
                defs.ui.TIME_PERIODS[:3],  # First 3 options
                key="class_time_period"
            )

            if st.button("Get Class Analytics") and class_id:
                with st.spinner("Generating class analytics..."):
                    result = self.api_client.get_class_analytics(class_id, time_period)

                    if "error" not in result:
                        st.success("✅ Class analytics generated!")

                        # Class metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Average Accuracy", f"{result.get('average_accuracy', 0)*100:.1f}%")
                        with col2:
                            st.metric("Top Performers", len(result.get("top_performers", [])))
                        with col3:
                            st.metric("Common Challenges", len(result.get("common_challenges", [])))

                        # Top performers
                        st.subheader("Top Performers")
                        for performer in result.get("top_performers", []):
                            st.success(f"• {performer}")

                        # Common challenges
                        st.subheader("Common Challenges")
                        for challenge in result.get("common_challenges", []):
                            st.warning(f"• {challenge}")
                    else:
                        st.error(f"Class analytics failed: {result['error']}")

        with tab3:
            st.subheader("Mistake Pattern Analysis")

            student_id = st.text_input("Student ID for Mistake Analysis", key="mistake_student")
            subject = st.selectbox("Subject", defs.ui.SUBJECTS[:4], key="mistake_subject")

            if st.button("Analyze Mistakes") and student_id:
                with st.spinner("Analyzing mistake patterns..."):
                    result = self.api_client.analyze_mistakes(student_id, subject)

                    if "error" not in result:
                        st.success("✅ Mistake analysis completed!")

                        # Mistake patterns
                        patterns = result.get("mistake_patterns", [])
                        if patterns:
                            st.subheader("Mistake Patterns")
                            df = pd.DataFrame(patterns)
                            st.dataframe(df)

                            # Visualization
                            fig = px.bar(df, x="pattern", y="frequency",
                                       title="Mistake Pattern Frequency")
                            st.plotly_chart(fig, width='stretch')

                        # Recommendations
                        recommendations = result.get("recommended_remediation", [])
                        if recommendations:
                            st.subheader("Recommended Remediation")
                            for rec in recommendations:
                                st.info(f"• {rec}")
                    else:
                        st.error(f"Mistake analysis failed: {result['error']}")

    def render_class_management(self) -> None:
        """Render class management interface"""
        st.title("👥 Class Management")
        st.info("Class management features coming soon...")

        # Placeholder for class management functionality
        st.write("Future features will include:")
        st.write("• Create and manage classes")
        st.write("• Add/remove students")
        st.write("• Assign exercises")
        st.write("• Track class progress")

    def render_settings(self) -> None:
        """Render settings interface"""
        st.title("⚙️ Settings")

        st.subheader("API Configuration")
        api_url = st.text_input(
            "API Base URL",
            value=self.api_client.base_url,
            help="URL of the EduAgent API server"
        )

        if st.button("Update API Settings"):
            self.api_client.base_url = api_url
            st.success("API settings updated!")

        st.subheader("System Information")
        if st.button("Check System Health"):
            with st.spinner("Checking system health..."):
                result = self.api_client.health_check()
                if "error" not in result:
                    st.success("✅ System is healthy!")
                    st.json(result)
                else:
                    st.error(f"Health check failed: {result['error']}")

    def run(self) -> None:
        """Main method to run the teacher interface"""
        selected_nav = self.render_sidebar()

        if selected_nav == "🏠 Dashboard":
            self.render_dashboard()
        elif selected_nav == "📖 Textbook Management":
            self.render_textbook_management()
        elif selected_nav == "❓ Question Generation":
            self.render_question_generation()
        elif selected_nav == "📊 Analytics & Reports":
            self.render_analytics()
        elif selected_nav == "👥 Class Management":
            self.render_class_management()
        elif selected_nav == "⚙️ Settings":
            self.render_settings()
