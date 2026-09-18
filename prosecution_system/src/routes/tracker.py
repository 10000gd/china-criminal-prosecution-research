# -*- coding: utf-8 -*-
"""案件跟踪路由"""
from flask import Blueprint, request, jsonify, render_template
from wenshu_updater import CaseTracker, ManualTracker

tracker_bp = Blueprint('tracker', __name__, url_prefix='')


@tracker_bp.route("/tracker/add", methods=["POST"])
def tracker_add():
    """添加案件跟踪"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    case_num = data.get("case_num", "")
    court = data.get("court", "")
    status = data.get("status", "investigating")

    tracker = CaseTracker()
    tracker.add_case(case_id, case_num, court, status)
    return jsonify({"success": True, "message": f"已添加案件跟踪: {case_id}"})


@tracker_bp.route("/tracker/update", methods=["POST"])
def tracker_update():
    """更新案件状态"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    new_status = data.get("status", "")
    event = data.get("event", "")

    tracker = CaseTracker()
    tracker.update_status(case_id, new_status, event=event)
    return jsonify({"success": True})


@tracker_bp.route("/tracker/remove", methods=["POST"])
def tracker_remove():
    """移除案件跟踪"""
    data = request.get_json()
    case_id = data.get("case_id", "")

    tracker = CaseTracker()
    tracker.remove_case(case_id)
    return jsonify({"success": True})


@tracker_bp.route("/tracker")
def tracker_page():
    """跟踪管理页面"""
    tracker = CaseTracker()
    cases = tracker.list_tracked()
    return render_template("tracker.html", tracked_cases=cases)


@tracker_bp.route("/tracker/log", methods=["POST"])
def tracker_log():
    """手动记录案件事件"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    event = data.get("event", "")
    source = data.get("source", "")

    manual = ManualTracker()
    manual.log_event(case_id, event, source=source)
    return jsonify({"success": True})
