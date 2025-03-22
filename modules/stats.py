# stats.py
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QLineSeries, QDateTimeAxis, QValueAxis

class StatsModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {
            "todo": [],
            "cards": [],
            "notes": [],
            "pomo": [],
            "music": []
        }
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 统计数据概览
        self.stats_summary = QLabel()
        self.stats_summary.setStyleSheet("font: 14px Segoe UI;")
        main_layout.addWidget(self.stats_summary)

        # 图表容器
        tab = QTabWidget()
        
        # 学习时间分布饼图
        self.pie_chart = QChart()
        self.pie_view = QChartView(self.pie_chart)
        tab.addTab(self.pie_view, "时间分布")

        # 学习趋势折线图
        self.line_chart = QChart()
        self.line_view = QChartView(self.line_chart)
        tab.addTab(self.line_view, "学习趋势")

        main_layout.addWidget(tab)
        self.setStyleSheet("""
            QChartView { background: white; border-radius: 8px; }
            QLabel { padding: 10px; background: white; border-radius: 8px; }
        """)

    def load_data(self):
        # 加载各模块数据
        try:
            with open(".json") as f:
                self.data["todo"] = json.load(f)
            with open("card_data.json") as f:
                self.data["cards"] = json.load(f)["cards"]
            with open("notes_data.json") as f:
                self.data["notes"] = json.load(f)["notes"]
            with open("pomo_data.json") as f:
                self.data["pomo"] = json.load(f)
        except Exception as e:
            print("数据加载错误:", e)

        self.update_charts()
        self.update_summary()

    def update_summary(self):
        # 计算核心指标
        completed_todos = len([t for t in self.data["todo"] if t["done"]])
        total_cards = len(self.data["cards"])
        study_time = sum([p["duration"] for p in self.data["pomo"] if p["is_work"]])
        note_count = len(self.data["notes"])

        text = f"""
        📊 学习统计概览：
        ✅ 完成任务：{completed_todos} 个
        🎴 记忆卡片：{total_cards} 张
        📝 创建笔记：{note_count} 篇
        ⏳ 总学习时间：{study_time} 分钟
        """
        self.stats_summary.setText(text)

    def update_charts(self):
        # 更新时间分布饼图
        pie_series = QPieSeries()
        categories = {
            "卡片学习": sum(1 for c in self.data["cards"] if c["proficiency"] > 0),
            "任务处理": len([t for t in self.data["todo"] if t["done"]]),
            "笔记编辑": len(self.data["notes"]),
            "番茄专注": len([p for p in self.data["pomo"] if p["is_work"]])
        }
        for name, value in categories.items():
            pie_series.append(name, value)
        
        self.pie_chart.removeAllSeries()
        self.pie_chart.addSeries(pie_series)
        self.pie_chart.setTitle("学习活动分布")
        self.pie_chart.setAnimationOptions(QChart.SeriesAnimations)

        # 更新学习趋势图
        line_series = QLineSeries()
        line_series.setName("每日学习时间")

        # 生成最近7天数据
        date_counts = {}
        for p in self.data["pomo"]:
            date = datetime.fromisoformat(p["timestamp"]).date()
            date_counts[date] = date_counts.get(date, 0) + p["duration"]

        today = datetime.today().date()
        for i in range(7):
            day = today - timedelta(days=6-i)
            value = date_counts.get(day, 0)

            # 转换为QDateTime
            qdt = QDateTime( QDate(day.year, day.month, day.day), QTime(0, 0) )
            line_series.append(qdt.toMSecsSinceEpoch(), value)

        self.line_chart.removeAllSeries()
        self.line_chart.addSeries(line_series)

        # 设置坐标轴
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM-dd")

        # 设置日期范围
        start_date = QDateTime(
            QDate((today - timedelta(days=6)).year,
            (today - timedelta(days=6)).month,
            (today - timedelta(days=6)).day))
        end_date = QDateTime(QDate(today.year, today.month, today.day))
        axis_x.setRange(start_date, end_date)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d 分钟")

        self.line_chart.addAxis(axis_x, Qt.AlignBottom)
        self.line_chart.addAxis(axis_y, Qt.AlignLeft)
        line_series.attachAxis(axis_x)
        line_series.attachAxis(axis_y)
        self.line_chart.setTitle("最近7天学习趋势")

    # 在main.py中的整合步骤：
    # 1. 添加导入
    # from stats import StatsModule
    
    # 2. 修改模块初始化
    # self.modules["统计"] = StatsModule()
    
    # 3. 在其他模块保存数据时触发更新：
    # def save_data(self):
    #     ...保存操作...
    #     self.parent().modules["统计"].load_data()