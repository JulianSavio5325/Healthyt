import sys
import sqlite3
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea, QFrame, QDialog,
                             QMessageBox, QToolTip, QSizePolicy, QDateEdit, QTabWidget, QSpacerItem)
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, QPoint, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QPainter, QBrush, QColor, QLinearGradient
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import uuid
import numpy as np
from datetime import datetime, timedelta

# Modern, sleek color palette
PRIMARY_BG = "#1A1C2C"  # Deep navy
SECONDARY_BG = "#25273A"  # Dark slate
CARD_BG = "#2E3147"  # Slate card
ACCENT_COLOR = "#FF2D55"  # Vibrant red (unused for buttons, kept for consistency)
TEXT_COLOR = "#E6E6FA"  # Light lavender
BORDER_COLOR = "#3B3F5C"  # Muted purple
SUBTLE_BORDER_COLOR = "#4A4E6E"  # Lighter subtle border color

# Button-specific colors
PRIMARY_COLOR = "#00C4B4"  # Green for proceed actions
PRIMARY_HOVER = "#00A89A"  # Darker green
SECONDARY_COLOR = "#6B7280"  # Gray for neutral actions
SECONDARY_HOVER = "#4B5563"  # Darker gray
DANGER_COLOR = "#FF4560"  # Red for delete actions
DANGER_HOVER = "#E03E54"  # Darker red
SUCCESS_COLOR = "#00A89A"  # Teal for success actions
SUCCESS_HOVER = "#008F86"  # Darker teal

CHART_COLORS = ["#FF2D55", "#00C4B4", "#FFB300", "#7E57C2", "#FF6F61", "#4CAF50"]  # Red, Teal, Amber, Purple, Coral, Green

DB = "meal_plans.db"

def get_connection():
    return sqlite3.connect(DB)

def init_database():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )""")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                meal_name TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                calories REAL DEFAULT 0.0,
                protein REAL DEFAULT 0.0,
                carbs REAL DEFAULT 0.0,
                fats REAL DEFAULT 0.0,
                preparation_time INTEGER DEFAULT 0,
                category TEXT DEFAULT 'Not Specified',
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plan_id) REFERENCES meal_plans(id)
            )""")
        conn.commit()

init_database()

def login_user(username, password):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()

def register_user(username, password):
    try:
        with get_connection() as conn:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def create_meal_plan(user_id, plan_name, date):
    with get_connection() as conn:
        conn.execute("INSERT INTO meal_plans (user_id, plan_name, date) VALUES (?, ?, ?)", 
                    (user_id, plan_name, date))
        conn.commit()

def delete_meal_plan(plan_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM meals WHERE plan_id=?", (plan_id,))
        conn.execute("DELETE FROM meal_plans WHERE id=?", (plan_id,))
        conn.commit()

def delete_all_plans(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM meals WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM meal_plans WHERE user_id=?", (user_id,))
        conn.commit()

def get_plans_for_user(user_id):
    with get_connection() as conn:
        return conn.execute("SELECT id, plan_name, date FROM meal_plans WHERE user_id=?", 
                          (user_id,)).fetchall()

def save_meal(user_id, plan_id, meal_name, meal_type, calories, protein, carbs, fats, 
              preparation_time, category):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO meals (user_id, plan_id, meal_name, meal_type, calories, protein, 
                             carbs, fats, preparation_time, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, plan_id, meal_name, meal_type, calories, protein, carbs, fats, 
              preparation_time, category))
        conn.commit()

def update_meal(meal_id, meal_name, meal_type, calories, protein, carbs, fats, 
                preparation_time, category):
    with get_connection() as conn:
        conn.execute("""
            UPDATE meals SET meal_name=?, meal_type=?, calories=?, protein=?, carbs=?, 
                           fats=?, preparation_time=?, category=?
            WHERE id=?
        """, (meal_name, meal_type, calories, protein, carbs, fats, preparation_time, 
              category, meal_id))
        conn.commit()

def update_username(user_id, new_username):
    try:
        with get_connection() as conn:
            conn.execute("UPDATE users SET username=? WHERE id=?", (new_username, user_id))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_meals_in_plan(plan_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, meal_name, meal_type, calories, protein, carbs, fats, 
                   preparation_time, category
            FROM meals WHERE plan_id=?
        """, (plan_id,)).fetchall()

def get_account_info(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM meal_plans WHERE user_id=?", (user_id,))
        plan_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM meals WHERE user_id=?", (user_id,))
        meal_count = cursor.fetchone()[0]
        return plan_count, meal_count

def delete_meal(meal_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM meals WHERE id=?", (meal_id,))
        conn.commit()

def get_plan_statistics(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT mp.id, mp.plan_name, mp.date, COUNT(m.id) as meal_count,
                   AVG(m.calories) as avg_calories,
                   SUM(m.protein) as total_protein,
                   SUM(m.carbs) as total_carbs,
                   SUM(m.fats) as total_fats
            FROM meal_plans mp
            LEFT JOIN meals m ON mp.id = m.plan_id AND m.user_id = ?
            WHERE mp.user_id = ?
            GROUP BY mp.id, mp.plan_name, mp.date
        """, (user_id, user_id))
        return cursor.fetchall()

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, button_type="primary"):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setMinimumHeight(45)
        self.setFont(QFont("Roboto", 11, QFont.Weight.Medium))
        
        base_color = {
            "primary": PRIMARY_COLOR,    # Green for proceed actions
            "secondary": SECONDARY_COLOR, # Gray for neutral actions
            "danger": DANGER_COLOR,      # Red for delete actions
            "success": SUCCESS_COLOR     # Teal for success actions
        }
        hover_color = {
            "primary": PRIMARY_HOVER,    # Darker green
            "secondary": SECONDARY_HOVER, # Darker gray
            "danger": DANGER_HOVER,      # Darker red
            "success": SUCCESS_HOVER     # Darker teal
        }

        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 {base_color[self.button_type]}, 
                                          stop:1 {base_color[self.button_type]}80);
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 {hover_color[self.button_type]}, 
                                          stop:1 {hover_color[self.button_type]}80);
                border: 1px solid {base_color[self.button_type]};
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 {hover_color[self.button_type]}80, 
                                          stop:1 {hover_color[self.button_type]}40);
            }}
        """)
        self.animation = QPropertyAnimation(self, b"maximumSize")
        self.animation.setDuration(150)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.animation.setStartValue(QSize(self.width(), self.height()))
        self.animation.setEndValue(QSize(self.width(), self.height() + 2))
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setStartValue(QSize(self.width(), self.height()))
        self.animation.setEndValue(QSize(self.width(), self.height() - 2))
        self.animation.start()
        super().leaveEvent(event)

class MealCreatorDialog(QDialog):
    def __init__(self, parent=None, meal_data=None, plan_id=None, user_id=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Meal")
        self.setMinimumSize(600, 600)
        self.setStyleSheet(f"background: {PRIMARY_BG};")
        self.meal_data = meal_data
        self.plan_id = plan_id
        self.user_id = user_id
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title = QLabel("Add/Edit Meal")
        title.setFont(QFont("Roboto", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        """)
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)

        fields = [
            ("Meal Name", QLineEdit(), "e.g., Grilled Chicken Salad"),
            ("Calories (kcal)", QLineEdit(), "e.g., 400"),
            ("Protein (g)", QLineEdit(), "e.g., 30"),
            ("Carbs (g)", QLineEdit(), "e.g., 45"),
            ("Fats (g)", QLineEdit(), "e.g., 15"),
            ("Prep Time (min)", QLineEdit(), "e.g., 20")
        ]

        self.name_entry, self.calories_entry, self.protein_entry, self.carbs_entry, self.fats_entry, self.prep_time_entry = [f[1] for f in fields]

        for idx, (label_text, widget, placeholder) in enumerate(fields):
            label = QLabel(label_text)
            label.setFont(QFont("Roboto", 11))
            label.setStyleSheet(f"color: {TEXT_COLOR};")
            widget.setPlaceholderText(placeholder)
            widget.setMinimumHeight(30)
            widget.setStyleSheet(f"""
                background-color: {SECONDARY_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                padding: 8px;
                color: {TEXT_COLOR};
                font-size: 12px;
            """)
            form_layout.addWidget(label, idx, 0)
            form_layout.addWidget(widget, idx, 1)

        self.type_box = QComboBox()
        self.type_box.addItems(["Breakfast", "Lunch", "Dinner", "Snack"])
        self.type_box.setMinimumHeight(30)
        self.type_box.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 8px;
            color: {TEXT_COLOR};
            font-size: 12px;
        """)
        form_layout.addWidget(QLabel("Meal Type"), len(fields), 0)
        form_layout.addWidget(self.type_box, len(fields), 1)

        self.category_box = QComboBox()
        self.category_box.addItems([
            "Not Specified",
            "Vegetarian",
            "Vegan",
            "Keto",
            "Gluten-Free",
            "Paleo",
            "Low-Carb",
            "High-Protein",
            "Dairy-Free",
            "Low-Fat",
            "Whole30",
            "Mediterranean",
            "Low-Sodium",
            "Pescatarian"
        ])
        self.category_box.setMinimumHeight(30)
        self.category_box.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 8px;
            color: {TEXT_COLOR};
            font-size: 12px;
        """)
        form_layout.addWidget(QLabel("Category"), len(fields) + 1, 0)
        form_layout.addWidget(self.category_box, len(fields) + 1, 1)

        main_layout.addWidget(form_frame)

        button_layout = QHBoxLayout()
        cancel_button = AnimatedButton("Cancel", button_type="secondary")
        cancel_button.clicked.connect(self.reject)
        submit_button = AnimatedButton("Save" if not self.meal_data else "Update", button_type="primary")
        submit_button.clicked.connect(self.submit)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(submit_button)
        main_layout.addLayout(button_layout)

        if self.meal_data:
            mid, mname, mtype, cal, pro, carb, fat, prep, cat = self.meal_data
            self.name_entry.setText(mname)
            self.type_box.setCurrentText(mtype)
            self.category_box.setCurrentText(cat)
            self.calories_entry.setText(str(cal))
            self.protein_entry.setText(str(pro))
            self.carbs_entry.setText(str(carb))
            self.fats_entry.setText(str(fat))
            self.prep_time_entry.setText(str(prep))

    def submit(self):
        mname = self.name_entry.text().strip()
        mtype = self.type_box.currentText()
        cat = self.category_box.currentText()
        try:
            cal = float(self.calories_entry.text().strip() or 0)
            pro = float(self.protein_entry.text().strip() or 0)
            carb = float(self.carbs_entry.text().strip() or 0)
            fat = float(self.carbs_entry.text().strip() or 0)
            prep = int(self.prep_time_entry.text().strip() or 0)
        except ValueError:
            QMessageBox.critical(self, "Error", "Please enter valid numbers for nutritional values and prep time.")
            return

        if mname:
            if cal < 0 or pro < 0 or carb < 0 or fat < 0 or prep < 0:
                QMessageBox.critical(self, "Error", "Nutritional values and prep time cannot be negative.")
                return
            if self.meal_data:
                update_meal(self.meal_data[0], mname, mtype, cal, pro, carb, fat, prep, cat)
            else:
                save_meal(self.user_id, self.plan_id, mname, mtype, cal, pro, carb, fat, prep, cat)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Please fill in the required field (Meal Name).")

class FigureCanvas(FigureCanvas):
    enlarged = pyqtSignal(object, object)

    def __init__(self, figure, meals_data, chart_type, parent=None):
        super().__init__(figure)
        self.meals_data = meals_data
        self.chart_type = chart_type
        self.parent_widget = parent
        self.figure.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.figure.canvas.mpl_connect('button_press_event', self.on_click)

    def on_hover(self, event):
        if event.inaxes:
            tooltip_text = None
            if self.chart_type == 'pie':
                for wedge, meals in self.meals_data.items():
                    if wedge.contains_point((event.x, event.y)):
                        tooltip_text = "\n".join([f"{m[1]}: {m[2]}" for m in meals])
                        break
            elif self.chart_type == 'bar':
                for bar, meals in self.meals_data.items():
                    if bar.contains_point((event.x, event.y)):
                        tooltip_text = "\n".join([f"{m[1]}" for m in meals])
                        break
            if tooltip_text:
                QToolTip.showText(self.mapToGlobal(QPoint(int(event.x), int(event.y))), tooltip_text, self)
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()

    def on_click(self, event):
        if event.button == 1:
            self.enlarged.emit(self.chart_type, self.figure)

class MealPlannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Healthyt")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1400, 900)  # Enforce minimum size to prevent resizing
        self.setStyleSheet(f"background: {PRIMARY_BG};")
        self.user_id = None
        self.username = ""
        self.selected_plan_id = None
        self.is_signup = False
        self.build_login_ui()

    def build_login_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left decorative panel
        left_panel = QFrame()
        left_panel.setFixedWidth(600)
        left_panel.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 #2E3147, stop:1 #00C4B4);
            border-right: 1px solid {SUBTLE_BORDER_COLOR};
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.setContentsMargins(50, 50, 50, 50)

        logo = QLabel("Healthyt")
        logo.setFont(QFont("Roboto", 48, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {TEXT_COLOR}; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); background: transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo)

        slogan = QLabel("Your Nutrition, simplified")
        slogan.setFont(QFont("Roboto", 18))
        slogan.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.8; background: transparent;")
        slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(slogan)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # Right form panel
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {PRIMARY_BG};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.setContentsMargins(50, 50, 50, 50)

        # Dynamic form container
        self.form_container = QFrame()
        self.form_container.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        """)
        self.form_layout = QVBoxLayout(self.form_container)
        self.form_layout.setSpacing(20)

        if not self.is_signup:
            # Login Form
            title = QLabel("Welcome Back")
            title.setFont(QFont("Roboto", 28, QFont.Weight.Bold))
            title.setStyleSheet(f"color: {TEXT_COLOR};")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.form_layout.addWidget(title)

            self.username_entry = QLineEdit()
            self.username_entry.setPlaceholderText("Username")
            self.username_entry.setFixedHeight(50)
            self.username_entry.setStyleSheet(f"""
                background-color: {SECONDARY_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                color: {TEXT_COLOR};
                font-size: 14px;
            """)
            self.form_layout.addWidget(self.username_entry)

            self.password_entry = QLineEdit()
            self.password_entry.setPlaceholderText("Password")
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_entry.setFixedHeight(50)
            self.password_entry.setStyleSheet(f"""
                background-color: {SECONDARY_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                color: {TEXT_COLOR};
                font-size: 14px;
            """)
            self.form_layout.addWidget(self.password_entry)

            login_button = AnimatedButton("Sign In", button_type="primary")
            login_button.clicked.connect(self.handle_login)
            self.form_layout.addWidget(login_button)

            signup_button = AnimatedButton("Sign Up", button_type="secondary")
            signup_button.clicked.connect(self.show_signup_form)
            self.form_layout.addWidget(signup_button)
        else:
            # Signup Form
            title = QLabel("Create Account")
            title.setFont(QFont("Roboto", 28, QFont.Weight.Bold))
            title.setStyleSheet(f"color: {TEXT_COLOR};")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.form_layout.addWidget(title)

            self.new_username_entry = QLineEdit()
            self.new_username_entry.setPlaceholderText("Username")
            self.new_username_entry.setFixedHeight(50)
            self.new_username_entry.setStyleSheet(f"""
                background-color: {SECONDARY_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                color: {TEXT_COLOR};
                font-size: 14px;
            """)
            self.form_layout.addWidget(self.new_username_entry)

            self.new_password_entry = QLineEdit()
            self.new_password_entry.setPlaceholderText("Password")
            self.new_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.new_password_entry.setFixedHeight(50)
            self.new_password_entry.setStyleSheet(f"""
                background-color: {SECONDARY_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                color: {TEXT_COLOR};
                font-size: 14px;
            """)
            self.form_layout.addWidget(self.new_password_entry)

            # Password suggestions
            password_hints = QLabel(
                "Password must be:\n- 8 characters minimum\n- Include a number\n- Include a special character\n- Include an uppercase letter"
            )
            password_hints.setFont(QFont("Roboto", 10))
            password_hints.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.7;")
            password_hints.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.form_layout.addWidget(password_hints)

            signup_button = AnimatedButton("Create Account", button_type="primary")
            signup_button.clicked.connect(self.handle_register)
            self.form_layout.addWidget(signup_button)

            back_button = AnimatedButton("Back to Login", button_type="secondary")
            back_button.clicked.connect(self.show_login_form)
            self.form_layout.addWidget(back_button)

        right_layout.addWidget(self.form_container)
        right_layout.addStretch()
        main_layout.addWidget(right_panel)

    def show_login_form(self):
        self.is_signup = False
        self.build_login_ui()

    def show_signup_form(self):
        self.is_signup = True
        self.build_login_ui()

    def handle_login(self):
        user = login_user(self.username_entry.text(), self.password_entry.text())
        if user:
            self.user_id = user[0]
            self.username = user[1]
            self.build_home_ui()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid credentials.")

    def handle_register(self):
        username = self.new_username_entry.text().strip()
        password = self.new_password_entry.text().strip()
        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isupper() for c in password) or not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            QMessageBox.critical(self, "Error", "Password must be 8 characters minimum and include a number, special character, and uppercase letter.")
            return
        if register_user(username, password):
            QMessageBox.information(self, "Success", "Account created successfully.")
            self.show_login_form()
        else:
            QMessageBox.critical(self, "Error", "Username already exists.")

    def build_header(self):
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                      stop:0 {PRIMARY_BG}, stop:1 {SECONDARY_BG});
            border-bottom: 1px solid {BORDER_COLOR};
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(15)

        logo = QLabel("Healthyt")
        logo.setFont(QFont("Roboto", 20, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {PRIMARY_COLOR}; background: transparent;")
        header_layout.addWidget(logo)

        header_layout.addStretch()

        home_button = AnimatedButton("Home", button_type="secondary")
        home_button.clicked.connect(self.build_home_ui)
        header_layout.addWidget(home_button)

        settings_button = AnimatedButton("Settings", button_type="secondary")
        settings_button.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_button)

        logout_button = AnimatedButton("Logout", button_type="danger")
        logout_button.clicked.connect(self.build_login_ui)
        header_layout.addWidget(logout_button)

        return header

    def build_home_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Fixed header
        header_frame = self.build_header()
        main_layout.addWidget(header_frame)

        # Content area with fixed height
        content_frame = QFrame()
        content_frame.setFixedHeight(620)  
        content_frame.setStyleSheet(f"background: {PRIMARY_BG};")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)  # Increased margins for less cramping
        content_layout.setSpacing(30)  # Increased spacing between elements

        hero_frame = QFrame()
        hero_frame.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                      stop:0 {CARD_BG}, stop:1 {SECONDARY_BG});
            border-radius: 16px;
            border: 1px solid {BORDER_COLOR};  # Subtle border
            padding: 30px;  # Increased padding for less cramping
        """)
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setSpacing(20)  # Increased spacing within hero

        title = QLabel(f"Welcome {self.username}")
        title.setFont(QFont("Roboto", 32, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent; line-height: 1.5em;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(title)

        desc = QLabel(
            "Effortlessly plan your meals, track nutrition, and gain insights into your dietary habits. "
            "Create personalized meal plans with a sleek, modern interface designed for nutrition enthusiasts."
        )
        desc.setFont(QFont("Roboto", 16))
        desc.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.8; background: transparent; line-height: 1.6em;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(desc)

        content_layout.addWidget(hero_frame)

        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 12px;
            border: 1px solid {SUBTLE_BORDER_COLOR};  # Subtle border
            padding: 25px;  # Increased padding
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(20, 20, 20, 20)  # Increased internal margins
        stats_layout.setSpacing(40)  # Increased spacing between stat cards

        plan_count, meal_count = get_account_info(self.user_id)
        stats_data = [
            ("Meal Plans", plan_count, ACCENT_COLOR),
            ("Total Meals", meal_count, SUCCESS_COLOR)
        ]

        for label_text, value, color in stats_data:
            stat_card = QFrame()
            stat_card.setStyleSheet(f"""
                background: {SECONDARY_BG};
                border-radius: 8px;
                border: 1px solid {SUBTLE_BORDER_COLOR};  # Subtle border
                padding: 20px;  # Increased padding
            """)
            stat_layout = QVBoxLayout(stat_card)
            stat_layout.setSpacing(15)  # Increased spacing within card
            stat_label = QLabel(label_text)
            stat_label.setFont(QFont("Roboto", 14))
            stat_label.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
            stat_layout.addWidget(stat_label)
            value_label = QLabel(str(value))
            value_label.setFont(QFont("Roboto", 24, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {color}; background: transparent; line-height: 1.5em;")
            stat_layout.addWidget(value_label)
            stats_layout.addWidget(stat_card)

        content_layout.addWidget(stats_frame)

        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 12px;
            border: 1px solid {SUBTLE_BORDER_COLOR};  # Subtle border
            padding: 25px;  # Increased padding
        """)
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(20, 20, 20, 20)  # Increased internal margins
        actions_layout.setSpacing(30)  # Increased spacing between buttons

        view_plans_button = AnimatedButton("Manage Plans", button_type="primary")
        view_plans_button.clicked.connect(self.build_main_ui)
        actions_layout.addWidget(view_plans_button)

        analytics_button = AnimatedButton("Nutrition Insights", button_type="primary")
        analytics_button.clicked.connect(self.build_analytics_ui)
        actions_layout.addWidget(analytics_button)

        content_layout.addWidget(actions_frame)

        main_layout.addWidget(content_frame)

    def build_analytics_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Fixed header
        header_frame = self.build_header()
        main_layout.addWidget(header_frame)

        # Content area with fixed height
        content_frame = QFrame()
        content_frame.setFixedHeight(620)  
        content_frame.setStyleSheet(f"background: {PRIMARY_BG};")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        title = QLabel("Nutrition Insights")
        title.setFont(QFont("Roboto", 28, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR}; background: transparent;")
        content_layout.addWidget(title)

        self.analytics_tab_widget = QTabWidget()
        self.analytics_tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {CARD_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 10px 10px 0 10px; /* Added top padding for gap */
            }}
            QTabBar {{
                alignment: center;
            }}
            QTabBar::tab {{
                background: {SECONDARY_BG};
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px 20px;
                margin-right: 10px;
                margin-left: 10px;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            QTabBar::tab:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 {PRIMARY_COLOR}, stop:1 {PRIMARY_COLOR}80);
                border: 1px solid {PRIMARY_COLOR};
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 {PRIMARY_COLOR}, stop:1 {PRIMARY_COLOR}60);
                color: {TEXT_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }}
        """)
        self.analytics_tab_widget.setMinimumSize(1200, 500)
        content_layout.addWidget(self.analytics_tab_widget)

        self.update_analytics()
        main_layout.addWidget(content_frame)

    def update_analytics(self):
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT mp.id, mp.plan_name, mp.date, m.id, m.meal_name, m.meal_type, 
                           m.calories, m.protein, m.carbs, m.fats, m.preparation_time, m.category
                    FROM meal_plans mp
                    LEFT JOIN meals m ON mp.id = m.plan_id AND m.user_id = ?
                    WHERE mp.user_id = ?
                """, (self.user_id, self.user_id))
                all_meals = cursor.fetchall()

            if not all_meals:
                no_data_label = QLabel("No meal plan or meal data available.")
                no_data_label.setFont(QFont("Roboto", 16))
                no_data_label.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.8;")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.analytics_tab_widget.clear()
                self.analytics_tab_widget.addTab(no_data_label, "No Data")
                return

            plan_data = {}
            for meal in all_meals:
                plan_id, plan_name, date, mid, mname, mtype, cal, pro, carb, fat, prep, cat = meal
                if plan_id and mid:
                    if plan_id not in plan_data:
                        plan_data[plan_id] = {'name': plan_name, 'date': date, 'meals': []}
                    plan_data[plan_id]['meals'].append((mid, mname, mtype, cal, pro, carb, fat, prep, cat))

            if plan_data:
                # 1. Macronutrient Distribution Pie Chart
                fig1, ax1 = plt.subplots(figsize=(12, 9))
                macro_counts = {'Protein': 0, 'Carbs': 0, 'Fats': 0}
                for plan_id, data in plan_data.items():
                    for _, _, _, _, pro, carb, fat, _, _ in data['meals']:
                        macro_counts['Protein'] += pro
                        macro_counts['Carbs'] += carb
                        macro_counts['Fats'] += fat
                total = sum(macro_counts.values())
                if total > 0:
                    labels = list(macro_counts.keys())
                    sizes = [v/total*100 for v in macro_counts.values()]
                    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                           textprops={'fontsize': 14, 'color': TEXT_COLOR},
                           colors=CHART_COLORS[:3])
                    ax1.axis('equal')
                    ax1.set_title("Macronutrient Distribution", color=TEXT_COLOR, fontsize=16)
                    fig1.patch.set_facecolor(CARD_BG)

                # 2. Calories by Meal Type Bar Chart
                fig2, ax2 = plt.subplots(figsize=(12, 9))
                meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
                calories = {t: 0 for t in meal_types}
                counts = {t: 0 for t in meal_types}
                for plan_id, data in plan_data.items():
                    for _, _, mtype, cal, _, _, _, _, _ in data['meals']:
                        if mtype in meal_types:
                            calories[mtype] += cal
                            counts[mtype] += 1
                avg_calories = [calories[t]/counts[t] if counts[t] > 0 else 0 for t in meal_types]
                if any(avg_calories):
                    bars = ax2.bar(meal_types, avg_calories, color=CHART_COLORS[0], edgecolor=BORDER_COLOR)
                    meals_data = {bar: [(0, mtype, f"{calories[mtype]/counts[mtype]:.1f} kcal")] for bar, mtype in zip(bars, meal_types) if counts[mtype] > 0}
                    ax2.set_ylabel('Average Calories (kcal)', color=TEXT_COLOR, fontsize=14)
                    ax2.set_title('Average Calories by Meal Type', color=TEXT_COLOR, fontsize=16)
                    ax2.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                    ax2.tick_params(colors=TEXT_COLOR, labelsize=12)

                # 3. Daily Calorie Trend Line Chart
                fig3, ax3 = plt.subplots(figsize=(12, 9))
                dates = sorted(set(data['date'] for data in plan_data.values()))
                daily_calories = []
                for date in dates:
                    total_cal = sum(
                        m[3] for pid, data in plan_data.items() 
                        if data['date'] == date for m in data['meals']
                    )
                    daily_calories.append(total_cal)
                if daily_calories:
                    ax3.plot(dates, daily_calories, marker='o', color=CHART_COLORS[1])
                    ax3.set_xlabel('Date', color=TEXT_COLOR, fontsize=14)
                    ax3.set_ylabel('Total Calories (kcal)', color=TEXT_COLOR, fontsize=14)
                    ax3.set_title('Daily Calorie Trend', color=TEXT_COLOR, fontsize=16)
                    ax3.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                    ax3.tick_params(axis='x', rotation=45, colors=TEXT_COLOR, labelsize=12)
                    ax3.tick_params(axis='y', colors=TEXT_COLOR, labelsize=12)

                # 4. Preparation Time by Meal Type Bar Chart
                fig4, ax4 = plt.subplots(figsize=(12, 9))
                prep_times = {t: 0 for t in meal_types}
                prep_counts = {t: 0 for t in meal_types}
                for plan_id, data in plan_data.items():
                    for _, _, mtype, _, _, _, _, prep, _ in data['meals']:
                        if mtype in meal_types:
                            prep_times[mtype] += prep
                            prep_counts[mtype] += 1
                avg_prep = [prep_times[t]/prep_counts[t] if prep_counts[t] > 0 else 0 for t in meal_types]
                if any(avg_prep):
                    bars = ax4.bar(meal_types, avg_prep, color=CHART_COLORS[2], edgecolor=BORDER_COLOR)
                    meals_data = {bar: [(0, mtype, f"{prep_times[mtype]/prep_counts[mtype]:.1f} min")] for bar, mtype in zip(bars, meal_types) if prep_counts[mtype] > 0}
                    ax4.set_ylabel('Average Prep Time (min)', color=TEXT_COLOR, fontsize=14)
                    ax4.set_title('Average Prep Time by Meal Type', color=TEXT_COLOR, fontsize=16)
                    ax4.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                    ax4.tick_params(colors=TEXT_COLOR, labelsize=12)

                # 5. Meal Category Distribution Pie Chart
                fig5, ax5 = plt.subplots(figsize=(12, 9))
                category_counts = {}
                for plan_id, data in plan_data.items():
                    for _, _, _, _, _, _, _, _, cat in data['meals']:
                        category_counts[cat] = category_counts.get(cat, 0) + 1
                if category_counts:
                    labels = list(category_counts.keys())
                    sizes = list(category_counts.values())
                    wedges, _, _ = ax5.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                                          textprops={'fontsize': 14, 'color': TEXT_COLOR},
                                          colors=CHART_COLORS[:len(labels)])
                    meals_data = {wedge: [(0, cat, f"{count} meals")] for wedge, cat, count in zip(wedges, labels, sizes)}
                    ax5.axis('equal')
                    ax5.set_title("Meal Category Distribution", color=TEXT_COLOR, fontsize=16)

                # 6. Protein Intake by Meal Type and Category Stacked Bar Chart
                fig6, ax6 = plt.subplots(figsize=(12, 9))
                meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
                categories = sorted(set(cat for data in plan_data.values() for _, _, _, _, _, _, _, _, cat in data['meals']))
                protein_data = {cat: [0] * len(meal_types) for cat in categories}
                counts = {cat: [0] * len(meal_types) for cat in categories}
                for plan_id, data in plan_data.items():
                    for _, _, mtype, _, pro, _, _, _, cat in data['meals']:
                        if mtype in meal_types:
                            idx = meal_types.index(mtype)
                            protein_data[cat][idx] += pro
                            counts[cat][idx] += 1
                bottom = np.zeros(len(meal_types))
                if any(sum(protein_data[cat]) > 0 for cat in categories):
                    for cat in categories:
                        avg_protein = [protein_data[cat][i]/counts[cat][i] if counts[cat][i] > 0 else 0 for i in range(len(meal_types))]
                        ax6.bar(meal_types, avg_protein, bottom=bottom, label=cat, color=CHART_COLORS[categories.index(cat) % len(CHART_COLORS)])
                        bottom += np.array(avg_protein)
                    ax6.set_ylabel('Average Protein (g)', color=TEXT_COLOR, fontsize=14)
                    ax6.set_title('Average Protein by Meal Type and Category', color=TEXT_COLOR, fontsize=16)
                    ax6.legend(fontsize=12, loc='upper right', facecolor=CARD_BG, edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR)
                    ax6.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                    ax6.tick_params(colors=TEXT_COLOR, labelsize=12)

                # Add tabs with enlarged visualizations
                self.analytics_tab_widget.clear()
                self.analytics_tab_widget.addTab(FigureCanvas(fig1, {}, 'pie', self), "Macronutrient Distribution")
                self.analytics_tab_widget.addTab(FigureCanvas(fig2, {}, 'bar', self), "Calories by Meal Type")
                self.analytics_tab_widget.addTab(FigureCanvas(fig3, {}, 'line', self), "Daily Calorie Trend")
                self.analytics_tab_widget.addTab(FigureCanvas(fig4, {}, 'bar', self), "Prep Time by Meal Type")
                self.analytics_tab_widget.addTab(FigureCanvas(fig5, {}, 'pie', self), "Meal Category Distribution")
                self.analytics_tab_widget.addTab(FigureCanvas(fig6, {}, 'bar', self), "Protein by Meal Type and Category")

                # Set initial size and style for all canvases
                for i in range(self.analytics_tab_widget.count()):
                    canvas = self.analytics_tab_widget.widget(i)
                    canvas.figure.patch.set_facecolor(CARD_BG)
                    canvas.setStyleSheet(f"background: {CARD_BG};")
                    canvas.enlarged.connect(self.enlarge_visualization)

        except Exception as e:
            error_label = QLabel(f"Error loading analytics: {str(e)}")
            error_label.setFont(QFont("Roboto", 16))
            error_label.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.8;")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.analytics_tab_widget.clear()
            self.analytics_tab_widget.addTab(error_label, "Error")

    def enlarge_visualization(self, chart_type, figure):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Enlarged {chart_type.capitalize()} View")
        dialog.setStyleSheet(f"background: {PRIMARY_BG};")
        layout = QVBoxLayout(dialog)
        dialog.setMinimumSize(1200, 900)

        figure.set_size_inches(15, 11)
        ax = figure.gca()
        ax.set_title(f"Enlarged {chart_type.capitalize()} View", fontsize=20, color=TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        if hasattr(ax, 'get_legend') and ax.get_legend():
            ax.get_legend().set_labelcolor(TEXT_COLOR)
        figure.patch.set_facecolor(CARD_BG)

        canvas = FigureCanvas(figure, {}, chart_type, self)
        layout.addWidget(canvas)
        canvas.draw()

        close_button = AnimatedButton("Close", button_type="secondary")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def build_main_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Fixed main header
        main_header_frame = self.build_header()
        main_layout.addWidget(main_header_frame)

        # Content area with fixed height
        content_frame = QFrame()
        content_frame.setFixedHeight(620)  
        content_frame.setStyleSheet(f"background: {PRIMARY_BG};")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Sidebar for Plans
        sidebar = QFrame()
        sidebar.setMinimumWidth(350)
        sidebar.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 16px;
            border: 1px solid {BORDER_COLOR};
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(15)

        plans_label = QLabel("Meal Plans")
        plans_label.setFont(QFont("Roboto", 18, QFont.Weight.Bold))
        plans_label.setStyleSheet(f"color: {TEXT_COLOR};")
        sidebar_layout.addWidget(plans_label)

        self.plan_list = QScrollArea()
        self.plan_list.setWidgetResizable(True)
        self.plan_list_content = QWidget()
        self.plan_list_layout = QVBoxLayout(self.plan_list_content)
        self.plan_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.plan_list_layout.setSpacing(10)
        self.plan_list.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget {{
                background: transparent;
            }}
        """)
        self.plan_list.setWidget(self.plan_list_content)
        sidebar_layout.addWidget(self.plan_list)

        plan_form_frame = QFrame()
        plan_form_frame.setStyleSheet(f"""
            background: {SECONDARY_BG};
            border-radius: 8px;
            border: 1px solid {BORDER_COLOR};
            padding: 10px;
        """)
        plan_form_layout = QVBoxLayout(plan_form_frame)
        plan_form_layout.setSpacing(10)

        self.plan_entry = QLineEdit()
        self.plan_entry.setPlaceholderText("New Plan Name (e.g., Weekly Plan)")
        self.plan_entry.setFixedHeight(45)
        self.plan_entry.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        plan_form_layout.addWidget(self.plan_entry)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMinimumHeight(45)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
            font-size: 12px;
        """)
        plan_form_layout.addWidget(self.date_edit)

        create_plan_button = AnimatedButton("Create Plan", button_type="primary")
        create_plan_button.clicked.connect(self.create_plan_ui)
        plan_form_layout.addWidget(create_plan_button)

        sidebar_layout.addWidget(plan_form_frame)

        delete_plan_button = AnimatedButton("Delete Selected Plan", button_type="danger")
        delete_plan_button.clicked.connect(self.delete_selected_plan)
        sidebar_layout.addWidget(delete_plan_button)

        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar)

        # Main Content Area
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 16px;
            border: 1px solid {BORDER_COLOR};
        """)
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Locked meal planning header
        self.meal_header_frame = QFrame()
        self.meal_header_frame.setFixedHeight(80)  # Locked height
        self.meal_header_frame.setStyleSheet(f"""
            background: {SECONDARY_BG};
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
        """)
        header_layout = QHBoxLayout(self.meal_header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(15)

        self.plan_title_label = QLabel("No Plan Selected")
        self.plan_title_label.setFont(QFont("Roboto", 20, QFont.Weight.Bold))
        self.plan_title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        header_layout.addWidget(self.plan_title_label)

        # Add button bar only if a plan is selected
        if self.selected_plan_id:
            button_bar = QFrame()
            button_bar.setFixedHeight(60)  # Fixed height for button bar
            button_bar_layout = QHBoxLayout(button_bar)
            button_bar_layout.setContentsMargins(0, 0, 0, 0)
            button_bar_layout.setSpacing(10)
            add_button = AnimatedButton("Add Meal", button_type="primary")
            add_button.clicked.connect(self.open_meal_creator)
            button_bar_layout.addWidget(add_button)
            button_bar_layout.addStretch()  # Push button to the right
            header_layout.addWidget(button_bar)

        self.main_layout.addWidget(self.meal_header_frame)

        # Scrollable meals section with tabs
        self.meals_scroll = QScrollArea()
        self.meals_scroll.setWidgetResizable(True)
        self.meals_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget {{
                background: transparent;
            }}
        """)
        self.meals_content = QWidget()
        self.meals_content.setStyleSheet(f"background: {CARD_BG};")
        self.meals_layout = QVBoxLayout(self.meals_content)
        self.meals_layout.setContentsMargins(0, 0, 0, 0)
        self.meals_layout.setSpacing(0)
        self.meals_scroll.setWidget(self.meals_content)
        self.main_layout.addWidget(self.meals_scroll, stretch=1)

        content_layout.addWidget(self.main_frame, stretch=1)
        main_layout.addWidget(content_frame)

        self.load_plans()

    def build_settings_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Fixed header
        header_frame = self.build_header()
        main_layout.addWidget(header_frame)

        # Content area with fixed height
        content_frame = QFrame()
        content_frame.setFixedHeight(620)  
        content_frame.setStyleSheet(f"background: {PRIMARY_BG};")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 16px;
            border: 1px solid {BORDER_COLOR};
        """)
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)

        title = QLabel("Account Settings")
        title.setFont(QFont("Roboto", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR};")
        settings_layout.addWidget(title)

        settings_buttons = [
            ("Change Password", self.open_change_password_dialog, "primary"),
            ("Update Username", self.open_update_username_dialog, "primary"),
            ("View Account Info", self.show_account_info, "primary"),
            ("Clear All Plans", self.confirm_clear_all_plans, "danger")
        ]

        for text, callback, button_type in settings_buttons:
            button = AnimatedButton(text, button_type=button_type)
            button.clicked.connect(callback)
            settings_layout.addWidget(button)

        settings_layout.addStretch()
        content_layout.addWidget(settings_frame)

        main_layout.addWidget(content_frame)

    def create_plan_ui(self):
        name = self.plan_entry.text().strip()
        date = self.date_edit.date().toString("yyyy-MM-dd")
        if name:
            create_meal_plan(self.user_id, name, date)
            self.plan_entry.clear()
            self.date_edit.setDate(QDate.currentDate())
            self.load_plans()

    def delete_selected_plan(self):
        if self.selected_plan_id:
            if QMessageBox.question(self, "Confirm", 
                                  f"Are you sure you want to delete the plan '{self.get_plan_name(self.selected_plan_id)}'? This action cannot be undone.",
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                delete_meal_plan(self.selected_plan_id)
                self.selected_plan_id = None
                self.load_plans()
                self.update_meal_header()
                self.clear_meals()
                QMessageBox.information(self, "Success", "Meal plan deleted successfully.")

    def get_plan_name(self, plan_id):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT plan_name FROM meal_plans WHERE id=?", (plan_id,))
            result = cursor.fetchone()
            return result[0] if result else "Unknown Plan"

    def load_plans(self):
        for i in reversed(range(self.plan_list_layout.count())):
            self.plan_list_layout.itemAt(i).widget().deleteLater()
        plans = get_plans_for_user(self.user_id)
        for pid, pname, date in plans:
            button = AnimatedButton(f"{pname} ({date})", button_type="secondary")
            button.clicked.connect(lambda checked, id=pid: self.open_plan(id))
            self.plan_list_layout.addWidget(button)

    def clear_meals(self):
        for i in reversed(range(self.meals_layout.count())):
            item = self.meals_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def open_plan(self, plan_id):
        self.selected_plan_id = plan_id
        self.update_meal_header()
        self.render_plan_meals()

    def update_meal_header(self):
        if self.selected_plan_id:
            self.plan_title_label.setText(self.get_plan_name(self.selected_plan_id))
        else:
            self.plan_title_label.setText("No Plan Selected")
        # Rebuild the header layout to reflect the current state
        for i in reversed(range(self.meal_header_frame.layout().count())):
            item = self.meal_header_frame.layout().itemAt(i)
            if item and item != self.meal_header_frame.layout().itemAt(0):  # Preserve the title label
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        if self.selected_plan_id:
            button_bar = QFrame()
            button_bar.setFixedHeight(60)  # Fixed height for button bar
            button_bar_layout = QHBoxLayout(button_bar)
            button_bar_layout.setContentsMargins(0, 0, 0, 0)
            button_bar_layout.setSpacing(10)
            add_button = AnimatedButton("Add Meal", button_type="primary")
            add_button.clicked.connect(self.open_meal_creator)
            button_bar_layout.addWidget(add_button)
            button_bar_layout.addStretch()  # Pushes button to the right
            self.meal_header_frame.layout().addWidget(button_bar)

    def render_plan_meals(self):
        self.clear_meals()

        meals = get_meals_in_plan(self.selected_plan_id)
        if meals:
            meal_tabs = QTabWidget()
            meal_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    background: {CARD_BG};
                    border: none;
                }}
                QTabBar::tab {{
                    background: {SECONDARY_BG};
                    color: {TEXT_COLOR};
                    border: 1px solid {BORDER_COLOR};
                    border-radius: 6px;
                    padding: 8px;
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background: {PRIMARY_COLOR};
                    color: {TEXT_COLOR};
                }}
            """)

            for meal in meals:
                mid, mname, mtype, cal, pro, carb, fat, prep, cat = meal
                tab_content = QWidget()
                tab_layout = QVBoxLayout(tab_content)
                tab_layout.setContentsMargins(10, 10, 10, 10)
                tab_layout.setSpacing(5)

                details_layout = QGridLayout()
                details_layout.setSpacing(5)
                details = [
                    ("Type", mtype, TEXT_COLOR),
                    ("Calories", f"{cal:.1f} kcal", ACCENT_COLOR),
                    ("Protein", f"{pro:.1f} g", SUCCESS_COLOR),
                    ("Carbs", f"{carb:.1f} g", CHART_COLORS[2]),
                    ("Fats", f"{fat:.1f} g", CHART_COLORS[3]),
                    ("Prep Time", f"{prep} min", TEXT_COLOR),
                    ("Category", cat, TEXT_COLOR)
                ]
                for idx, (label, value, color) in enumerate(details):
                    lbl = QLabel(label)
                    lbl.setStyleSheet(f"color: {TEXT_COLOR}; font-weight: bold;")
                    val = QLabel(value)
                    val.setStyleSheet(f"color: {color};")
                    details_layout.addWidget(lbl, idx, 0)
                    details_layout.addWidget(val, idx, 1)
                tab_layout.addLayout(details_layout)

                actions_layout = QHBoxLayout()
                edit_button = AnimatedButton("Edit", button_type="success")
                edit_button.clicked.connect(lambda checked, m=meal: self.open_meal_editor(m))
                delete_button = AnimatedButton("Delete", button_type="danger")
                delete_button.clicked.connect(lambda checked, m=mid: self.remove_meal(m))
                actions_layout.addWidget(edit_button)
                actions_layout.addWidget(delete_button)
                tab_layout.addLayout(actions_layout)

                tab_content.setLayout(tab_layout)
                meal_tabs.addTab(tab_content, mname)

            self.meals_layout.addWidget(meal_tabs)
        else:
            no_meals = QLabel("No meals added yet. Click 'Add Meal' to get started!")
            no_meals.setFont(QFont("Roboto", 16))
            no_meals.setStyleSheet(f"color: {TEXT_COLOR}; opacity: 0.8;")
            no_meals.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.meals_layout.addWidget(no_meals)

    def open_meal_creator(self):
        dialog = MealCreatorDialog(self, plan_id=self.selected_plan_id, user_id=self.user_id)
        if dialog.exec():
            self.render_plan_meals()

    def open_meal_editor(self, meal_data):
        dialog = MealCreatorDialog(self, meal_data=meal_data, plan_id=self.selected_plan_id, user_id=self.user_id)
        if dialog.exec():
            self.render_plan_meals()

    def display_mini_dashboard(self, dashboard_layout):
        try:
            meals = get_meals_in_plan(self.selected_plan_id)
            if not meals:
                return

            # Macronutrient Pie Chart
            fig1, ax1 = plt.subplots(figsize=(5, 4))
            macros = {'Protein': 0, 'Carbs': 0, 'Fats': 0}
            for meal in meals:
                _, _, _, _, pro, carb, fat, _, _ = meal
                macros['Protein'] += pro
                macros['Carbs'] += carb
                macros['Fats'] += fat
            total = sum(macros.values())
            if total > 0:
                labels = list(macros.keys())
                sizes = [v/total*100 for v in macros.values()]
                ax1.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90,
                       textprops={'fontsize': 10, 'color': TEXT_COLOR},
                       colors=CHART_COLORS[:3])
                ax1.axis('equal')
                fig1.patch.set_facecolor(CARD_BG)
                macro_frame = QFrame()
                macro_frame.setStyleSheet(f"""
                    background: {SECONDARY_BG};
                    border-radius: 8px;
                    border: 1px solid {BORDER_COLOR};
                    padding: 10px;
                """)
                macro_layout = QVBoxLayout(macro_frame)
                title_label = QLabel("Macros")
                title_label.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
                title_label.setStyleSheet(f"color: {TEXT_COLOR};")
                macro_layout.addWidget(title_label)
                canvas1 = FigureCanvas(fig1, {}, 'pie', self)
                canvas1.enlarged.connect(self.enlarge_visualization)
                macro_layout.addWidget(canvas1)
                dashboard_layout.addWidget(macro_frame)

            # Calories Bar Chart
            fig2, ax2 = plt.subplots(figsize=(5, 4))
            meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Snack']
            calories = {t: 0 for t in meal_types}
            counts = {t: 0 for t in meal_types}
            for meal in meals:
                _, _, mtype, cal, _, _, _, _, _ = meal
                if mtype in meal_types:
                    calories[mtype] += cal
                    counts[mtype] += 1
            avg_calories = [calories[t]/counts[t] if counts[t] > 0 else 0 for t in meal_types]
            if any(avg_calories):
                ax2.bar(meal_types, avg_calories, color=CHART_COLORS[0], edgecolor=BORDER_COLOR)
                ax2.set_ylabel('Calories', color=TEXT_COLOR, fontsize=10)
                ax2.tick_params(axis='x', rotation=45, labelsize=10, colors=TEXT_COLOR)
                ax2.tick_params(axis='y', labelsize=10, colors=TEXT_COLOR)
                ax2.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                fig2.patch.set_facecolor(CARD_BG)
                bar_frame = QFrame()
                bar_frame.setStyleSheet(f"""
                    background: {SECONDARY_BG};
                    border-radius: 8px;
                    border: 1px solid {BORDER_COLOR};
                    padding: 10px;
                """)
                bar_layout = QVBoxLayout(bar_frame)
                title_label = QLabel("Calories")
                title_label.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
                title_label.setStyleSheet(f"color: {TEXT_COLOR};")
                bar_layout.addWidget(title_label)
                canvas2 = FigureCanvas(fig2, {}, 'bar', self)
                canvas2.enlarged.connect(self.enlarge_visualization)
                bar_layout.addWidget(canvas2)
                dashboard_layout.addWidget(bar_frame)

            # Prep Time Bar Chart
            fig3, ax3 = plt.subplots(figsize=(5, 4))
            prep_times = {t: 0 for t in meal_types}
            prep_counts = {t: 0 for t in meal_types}
            for meal in meals:
                _, _, mtype, _, _, _, _, prep, _ = meal
                if mtype in meal_types:
                    prep_times[mtype] += prep
                    prep_counts[mtype] += 1
            avg_prep = [prep_times[t]/prep_counts[t] if prep_counts[t] > 0 else 0 for t in meal_types]
            if any(avg_prep):
                ax3.bar(meal_types, avg_prep, color=CHART_COLORS[1], edgecolor=BORDER_COLOR)
                ax3.set_ylabel('Prep Time (min)', color=TEXT_COLOR, fontsize=10)
                ax3.tick_params(axis='x', rotation=45, labelsize=10, colors=TEXT_COLOR)
                ax3.tick_params(axis='y', labelsize=10, colors=TEXT_COLOR)
                ax3.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR)
                fig3.patch.set_facecolor(CARD_BG)
                prep_frame = QFrame()
                prep_frame.setStyleSheet(f"""
                    background: {SECONDARY_BG};
                    border-radius: 8px;
                    border: 1px solid {BORDER_COLOR};
                    padding: 10px;
                """)
                prep_layout = QVBoxLayout(prep_frame)
                title_label = QLabel("Prep Time")
                title_label.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
                title_label.setStyleSheet(f"color: {TEXT_COLOR};")
                prep_layout.addWidget(title_label)
                canvas3 = FigureCanvas(fig3, {}, 'bar', self)
                canvas3.enlarged.connect(self.enlarge_visualization)
                prep_layout.addWidget(canvas3)
                dashboard_layout.addWidget(prep_frame)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate dashboard: {str(e)}")

    def remove_meal(self, meal_id):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT meal_name FROM meals WHERE id=?", (meal_id,))
            meal_name = cursor.fetchone()
        if meal_name:
            if QMessageBox.question(self, "Confirm", 
                                  f"Are you sure you want to delete the meal '{meal_name[0]}'? This action cannot be undone.",
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                delete_meal(meal_id)
                self.render_plan_meals()
                QMessageBox.information(self, "Success", "Meal deleted successfully.")

    def open_settings(self):
        self.build_settings_ui()

    def open_change_password_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Password")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet(f"background: {PRIMARY_BG};")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Change Password")
        title.setFont(QFont("Roboto", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title)

        current_password = QLineEdit()
        current_password.setPlaceholderText("Current Password")
        current_password.setEchoMode(QLineEdit.EchoMode.Password)
        current_password.setMinimumHeight(30)
        current_password.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        layout.addWidget(current_password)

        new_password = QLineEdit()
        new_password.setPlaceholderText("New Password")
        new_password.setEchoMode(QLineEdit.EchoMode.Password)
        new_password.setMinimumHeight(30)
        new_password.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        layout.addWidget(new_password)

        confirm_password = QLineEdit()
        confirm_password.setPlaceholderText("Confirm New Password")
        confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_password.setMinimumHeight(30)
        confirm_password.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        layout.addWidget(confirm_password)

        button_layout = QHBoxLayout()
        cancel_button = AnimatedButton("Cancel", button_type="secondary")
        cancel_button.clicked.connect(dialog.reject)
        submit_button = AnimatedButton("Update", button_type="primary")
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(submit_button)
        layout.addLayout(button_layout)

        def submit():
            if not all([current_password.text(), new_password.text(), confirm_password.text()]):
                QMessageBox.critical(dialog, "Error", "All fields are required.")
                return
            user = login_user(self.username, current_password.text())
            if not user:
                QMessageBox.critical(dialog, "Error", "Current password is incorrect.")
                return
            if new_password.text() != confirm_password.text():
                QMessageBox.critical(dialog, "Error", "New passwords do not match.")
                return
            with get_connection() as conn:
                conn.execute("UPDATE users SET password=? WHERE id=?", (new_password.text(), self.user_id))
                conn.commit()
            QMessageBox.information(dialog, "Success", "Password updated successfully.")
            dialog.accept()

        submit_button.clicked.connect(submit)
        dialog.exec()

    def open_update_username_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Update Username")
        dialog.setMinimumSize(500, 350)
        dialog.setStyleSheet(f"background: {PRIMARY_BG};")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Update Username")
        title.setFont(QFont("Roboto", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title)

        new_username = QLineEdit()
        new_username.setPlaceholderText("New Username")
        new_username.setMinimumHeight(30)
        new_username.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        layout.addWidget(new_username)

        password = QLineEdit()
        password.setPlaceholderText("Current Password")
        password.setEchoMode(QLineEdit.EchoMode.Password)
        password.setMinimumHeight(30)
        password.setStyleSheet(f"""
            background-color: {SECONDARY_BG};
            border: 1px solid {BORDER_COLOR};
            border-radius: 6px;
            padding: 10px;
            color: {TEXT_COLOR};
        """)
        layout.addWidget(password)

        button_layout = QHBoxLayout()
        cancel_button = AnimatedButton("Cancel", button_type="secondary")
        cancel_button.clicked.connect(dialog.reject)
        submit_button = AnimatedButton("Update", button_type="primary")
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(submit_button)
        layout.addLayout(button_layout)

        def submit():
            if not all([new_username.text(), password.text()]):
                QMessageBox.critical(dialog, "Error", "All fields are required.")
                return
            user = login_user(self.username, password.text())
            if not user:
                QMessageBox.critical(dialog, "Error", "Password is incorrect.")
                return
            if update_username(self.user_id, new_username.text()):
                self.username = new_username.text()
                QMessageBox.information(dialog, "Success", "Username updated successfully.")
                dialog.accept()
                self.build_settings_ui()  # Refresh settings page with new username
            else:
                QMessageBox.critical(dialog, "Error", "Username already exists.")

        submit_button.clicked.connect(submit)
        dialog.exec()

    def show_account_info(self):
        plan_count, meal_count = get_account_info(self.user_id)
        dialog = QDialog(self)
        dialog.setWindowTitle("Account Information")
        dialog.setMinimumSize(500, 400)
        dialog.setStyleSheet(f"background: {PRIMARY_BG};")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Account Information")
        title.setFont(QFont("Roboto", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            background: {CARD_BG};
            border-radius: 12px;
            border: 1px solid {BORDER_COLOR};
            padding: 15px;
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)

        info_data = [
            (f"Username: {self.username}", TEXT_COLOR),
            (f"Total Meal Plans: {plan_count}", PRIMARY_COLOR),
            (f"Total Meals: {meal_count}", SUCCESS_COLOR)
        ]

        for text, color in info_data:
            label = QLabel(text)
            label.setFont(QFont("Roboto", 14))
            label.setStyleSheet(f"color: {color};")
            info_layout.addWidget(label)

        layout.addWidget(info_frame)

        close_button = AnimatedButton("Close", button_type="secondary")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        layout.addStretch()
        dialog.exec()

    def confirm_clear_all_plans(self):
        if QMessageBox.question(self, "Confirm",
                              "Are you sure you want to delete ALL meal plans and meals? This action cannot be undone.",
                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            delete_all_plans(self.user_id)
            self.build_settings_ui()  # Refresh the settings page after clearing the meal plans
            QMessageBox.information(self, "Success", "All meal plans and meals deleted successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MealPlannerApp()
    window.show()
    sys.exit(app.exec())