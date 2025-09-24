"""
EduAgent UI Module
Streamlit-based web interfaces for teachers and students
"""

from .main import run_interface
from .student_interface import StudentInterface
from .teacher_interface import TeacherInterface

__all__ = ["StudentInterface", "TeacherInterface", "run_interface"]
