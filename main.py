import datetime
import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QGridLayout, QCheckBox,
                             QTableWidget, QTableWidgetItem, QDialog, QDialogButtonBox, QInputDialog, QCalendarWidget,
                             QListWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Goal Tracker")
        self.setGeometry(100, 100, 1200, 800)
        self.conn = self.create_connection()
        self.create_tables()
        self.initUI()
        self.load_goals()

    def initUI(self):
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout()
        self.centralWidget.setLayout(self.layout)
        button_css = """
        font-size: 24px;
        """
        self.addButton = QPushButton("Добавить цель")
        self.addButton.setStyleSheet(button_css)
        self.openCalendar = QPushButton("Открыть календрь")
        self.openCalendar.setStyleSheet(button_css)
        self.addButton.clicked.connect(self.add_goal)
        self.openCalendar.clicked.connect(self.open_calendar)
        self.layout.addWidget(self.addButton)
        self.layout.addWidget(self.openCalendar)

        table_css = """
        font-size: 24px;
        """
        self.goalsTable = QTableWidget()
        self.goalsTable.setStyleSheet(table_css)
        self.goalsTable.setColumnCount(3)
        self.goalsTable.setHorizontalHeaderLabels(["Цель", "Кол-во часов", "Подробнее"])
        self.layout.addWidget(self.goalsTable)

        self.load_goals()

    def open_calendar(self):
        self.openCalendar = Calendar(self)
        self.openCalendar.show()

    def load_goals(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, hours FROM Goals")
        goals = cursor.fetchall()

        self.goalsTable.setRowCount(0)
        for row_number, goal in enumerate(goals):
            self.goalsTable.insertRow(row_number)
            self.goalsTable.setItem(row_number, 0, QTableWidgetItem(goal[1]))
            self.goalsTable.setItem(row_number, 1, QTableWidgetItem(str(goal[2])))

            detailsButton = QPushButton("Подробнее")
            detailsButton.clicked.connect(lambda checked, goal_id=goal[0]: self.open_goal_details(goal_id))
            self.goalsTable.setCellWidget(row_number, 2, detailsButton)

            deleteButton = QPushButton("Удалить")
            deleteButton.clicked.connect(lambda checked, goal_id=goal[0]: self.delete_goal(goal_id))
            self.goalsTable.setCellWidget(row_number, 4, deleteButton)
            self.update_goal_completion(goal[0])

    def delete_goal(self, goal_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM Goals WHERE id = ?", (goal_id,))
        self.conn.commit()
        self.load_goals()

    def create_connection(self):
        try:
            conn = sqlite3.connect("goals.db")
            return conn
        except sqlite3.Error as e:
            print(e)
            return None

    def create_tables(self):
        create_goals_table = """CREATE TABLE IF NOT EXISTS Goals (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                hours INTEGER NOT NULL);
                            """
        create_tasks_table = """CREATE TABLE IF NOT EXISTS Tasks (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                goal_id INTEGER NOT NULL,
                                description TEXT NOT NULL,
                                completed BOOLEAN NOT NULL DEFAULT 0,
                                hours INTEGER NOT NULL,
                                deadline DATE,
                                FOREIGN KEY (goal_id) REFERENCES Goals (id));
                            """
        cursor = self.conn.cursor()
        cursor.execute(create_goals_table)
        cursor.execute(create_tasks_table)
        self.conn.commit()

    def add_goal(self):
        self.addGoalDialog = AddGoalDialog(self)
        self.addGoalDialog.show()

    def update_goal_progress(self, goal_id):

        cursor = self.conn.cursor()
        cursor.execute("SELECT hours FROM Goals WHERE id = ?", (goal_id,))
        total_hours = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(hours) FROM tasks WHERE goal_id=? AND completed=1", (goal_id,))
        completed_hours = cursor.fetchone()[0] or 0

        progress = int((completed_hours / total_hours) * 100 if total_hours else 0)
        return progress

    def update_goal_completion(self, goal_id):
        cursor = self.conn.cursor()
        name = cursor.execute("SELECT name FROM Goals WHERE id = ?", (goal_id,)).fetchone()[0]
        row_count = self.goalsTable.rowCount()
        current_row = 0
        for row in range(row_count):
            if self.goalsTable.item(row, 0).text() == name:
                progress = self.update_goal_progress(goal_id)
                self.goalsTable.setItem(row, 3, QTableWidgetItem(f"{progress}%"))

    def init_goals_table(self):
        self.goalsTable.setColumnCount(5)
        self.goalsTable.setHorizontalHeaderLabels(["Цель", "Кол-во часов", "Подробнее", "Прогресс", "Удалить"])
        self.goalsTable.setColumnWidth(0, 400)
        self.goalsTable.setColumnWidth(1, 200)
        self.goalsTable.setColumnWidth(2, 200)
        self.goalsTable.setColumnWidth(3, 200)

    def start(self):
        self.initUI()
        self.init_goals_table()
        self.load_goals()
        self.show()

    def open_goal_details(self, goal_id):
        self.goalDetailsWindow = GoalDetailsWindow(goal_id, self)
        self.goalDetailsWindow.exec_()


class Calendar(QWidget):
    def __init__(self, parent):
        super(Calendar, self).__init__()
        loadUi("calendar.ui", self)
        self.calendarWidget.selectionChanged.connect(self.calendarDateChanged)
        self.calendarDateChanged()
        self.parent = parent

    def calendarDateChanged(self):
        dateSelected = self.calendarWidget.selectedDate().toPyDate()
        self.updateTaskList(dateSelected)

    def updateTaskList(self, date):
        self.tasksListWidget.clear()

        db = sqlite3.connect("goals.db")
        cursor = db.cursor()

        query = "SELECT description, completed FROM Tasks WHERE deadline = ?"
        row = (date,)
        results = cursor.execute(query, row).fetchall()
        for result in results:
            item = QListWidgetItem(str(result[0]))
            self.tasksListWidget.addItem(item)


class AddGoalDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Добавить цель")
        self.setGeometry(100, 100, 400, 300)
        self.layout = QVBoxLayout(self)
        self.setStyleSheet("font-size: 24px;")

        self.nameInput = QLineEdit(self)
        self.hoursInput = QLineEdit(self)
        self.layout.addWidget(QLabel("Название цели:"))
        self.layout.addWidget(self.nameInput)
        self.layout.addWidget(QLabel("Количество часов:"))
        self.layout.addWidget(self.hoursInput)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def accept(self):
        goal_name = self.nameInput.text()
        goal_hours = self.hoursInput.text()
        if goal_name and goal_hours.isdigit():
            self.insert_goal(goal_name, int(goal_hours))
            super().accept()
        else:
            pass

    def insert_goal(self, name, hours):
        conn = self.parent().create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Goals (name, hours) VALUES (?, ?)", (name, hours))
        conn.commit()
        self.parent().load_goals()


class GoalDetailsWindow(QDialog):
    def __init__(self, goal_id, parent):
        super().__init__(parent)
        self.goal_id = goal_id
        self.setWindowTitle("Детали цели")
        self.setGeometry(100, 100, 1000, 600)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        table_css = """
        font-size: 24px;
        """
        button_css = """
        font-size: 24px;
        """

        self.tasksTable = QTableWidget()
        self.tasksTable.setColumnCount(4)
        self.tasksTable.setStyleSheet(table_css)
        self.tasksTable.setHorizontalHeaderLabels(['Задача', 'Выполнено', "Вес в ч.", 'Удалить'])
        self.tasksTable.setColumnWidth(0, 300)
        self.tasksTable.setColumnWidth(1, 200)
        self.tasksTable.setColumnWidth(2, 200)
        self.tasksTable.setColumnWidth(3, 200)
        self.layout.addWidget(self.tasksTable)

        self.addButton = QPushButton("Добавить задачу")
        self.addButton.setStyleSheet(button_css)
        self.addButton.clicked.connect(self.add_task)
        self.layout.addWidget(self.addButton)

        self.load_tasks()

    def load_tasks(self):
        cursor = self.parent().conn.cursor()
        cursor.execute("SELECT id, description, completed, hours FROM Tasks WHERE goal_id = ?", (self.goal_id,))
        tasks = cursor.fetchall()

        self.tasksTable.setRowCount(0)
        for row_number, task in enumerate(tasks):
            self.tasksTable.insertRow(row_number)
            self.tasksTable.setItem(row_number, 0, QTableWidgetItem(task[1]))

            completedCheckbox = QCheckBox(self.tasksTable)
            completedCheckbox.setChecked(task[2] == 1)
            completedCheckbox.stateChanged.connect(
                lambda state, task_id=task[0]: self.toggle_task_completed(state, task_id))
            self.tasksTable.setCellWidget(row_number, 1, completedCheckbox)

            self.tasksTable.setItem(row_number, 2, QTableWidgetItem(str(task[3])))

            deleteButton = QPushButton("Удалить")
            deleteButton.clicked.connect(lambda checked, task_id=task[0]: self.delete_task(task_id))
            self.tasksTable.setCellWidget(row_number, 3, deleteButton)

    def toggle_task_completed(self, state, task_id):
        cursor = self.parent().conn.cursor()
        cursor.execute("UPDATE Tasks SET completed = ? WHERE id = ?", (state == Qt.Checked, task_id))
        self.parent().conn.commit()
        self.update_goal_completion_percentage()

    def delete_task(self, task_id):
        cursor = self.parent().conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE id = ?", (task_id,))
        self.parent().conn.commit()
        self.load_tasks()
        self.update_goal_completion_percentage()

    def update_goal_completion_percentage(self):
        percentage = self.update_goal_progress(self.goal_id)
        self.parent().update_goal_completion(self.goal_id)

    def update_goal_progress(self, goal_id):

        cursor = self.parent().conn.cursor()
        cursor.execute("SELECT SUM(hours) FROM Tasks WHERE goal_id = ?", (goal_id,))
        total_hours = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(hours) FROM tasks WHERE goal_id=? AND completed=1", (goal_id,))
        completed_hours = cursor.fetchone()[0] or 0

        progress = (completed_hours / total_hours) * 100 if total_hours else 0
        return progress

    def add_task(self):
        text, ok = QInputDialog.getText(self, "Добавить задачу", "Описание задачи:", QLineEdit.Normal)
        if ok and text:
            hours, ok = QInputDialog.getText(self, "Добавить задачу", "Вес задачи(в часах):", QLineEdit.Normal)
            if ok and hours:
                deadline, ok = QInputDialog.getText(self, "Добавить задачу", "Дедлайн задачи(DD/MM/YYYYY)",
                                                    QLineEdit.Normal)
                if len(deadline) != 0:
                    deadline = datetime.datetime.strptime(deadline.replace("/", ""), "%d%m%Y").date()
                cursor = self.parent().conn.cursor()
                cursor.execute("INSERT INTO Tasks (goal_id, description, hours, deadline) VALUES (?, ?, ?, ?)",
                               (self.goal_id, text, hours, deadline))
                self.parent().conn.commit()
                self.load_tasks()
        self.update_goal_completion_percentage()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.start()
    sys.excepthook = except_hook
    sys.exit(app.exec_())
