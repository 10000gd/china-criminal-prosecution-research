# -*- coding: utf-8 -*-
"""
WebSocket通知模块 - notifications.py

功能：
- 实时推送系统通知
- 用户收藏更新通知
- 量刑分析完成通知
- 案件状态变更通知
"""

from flask import request, session
from datetime import datetime
import json

# 全局SocketIO实例（可选）
socketio = None

def init_socketio(app):
    """初始化SocketIO（可选功能）"""
    global socketio
    try:
        from flask_socketio import SocketIO, emit, join_room, leave_room
        
        socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            ping_timeout=60,
            ping_interval=25,
        )
        
        # 注册事件处理器
        register_handlers(socketio)
        
        return socketio
    except ImportError:
        print("⚠️ flask-socketio 未安装，WebSocket功能不可用")
        return None


def register_handlers(sio):
    """注册SocketIO事件处理器"""
    
    @sio.on('connect')
    def handle_connect():
        """处理连接"""
        user_id = session.get('user_id')
        if user_id:
            # 加入用户专属房间
            join_room(f'user_{user_id}')
            print(f"✅ 用户 {user_id} 已连接 WebSocket")
        else:
            # 加入公共房间
            join_room('public')
            print("✅ 访客已连接 WebSocket")
        
        emit('connected', {
            'status': 'connected',
            'timestamp': datetime.now().isoformat(),
        })
    
    @sio.on('disconnect')
    def handle_disconnect():
        """处理断开连接"""
        user_id = session.get('user_id')
        if user_id:
            leave_room(f'user_{user_id}')
            print(f"✅ 用户 {user_id} 已断开 WebSocket")
        else:
            leave_room('public')
            print("✅ 访客已断开 WebSocket")
    
    @sio.on('subscribe')
    def handle_subscribe(data):
        """订阅频道"""
        channel = data.get('channel', '')
        if channel:
            join_room(channel)
            emit('subscribed', {
                'channel': channel,
                'timestamp': datetime.now().isoformat(),
            })
    
    @sio.on('unsubscribe')
    def handle_unsubscribe(data):
        """取消订阅"""
        channel = data.get('channel', '')
        if channel:
            leave_room(channel)
            emit('unsubscribed', {
                'channel': channel,
                'timestamp': datetime.now().isoformat(),
            })
    
    @sio.on('ping')
    def handle_ping():
        """心跳检测"""
        emit('pong', {'timestamp': datetime.now().isoformat()})


def send_notification(user_id: str, notification: dict):
    """向指定用户发送通知"""
    if socketio:
        socketio.emit('notification', {
            'user_id': user_id,
            'type': notification.get('type', 'info'),
            'title': notification.get('title', ''),
            'message': notification.get('message', ''),
            'data': notification.get('data'),
            'timestamp': datetime.now().isoformat(),
        }, room=f'user_{user_id}')


def send_broadcast(notification: dict):
    """广播通知给所有用户"""
    if socketio:
        socketio.emit('broadcast', {
            'type': notification.get('type', 'info'),
            'title': notification.get('title', ''),
            'message': notification.get('message', ''),
            'timestamp': datetime.now().isoformat(),
        }, room='public')


def send_system_message(message: str, level: str = 'info'):
    """发送系统消息"""
    if socketio:
        socketio.emit('system_message', {
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat(),
        })


def notify_favorite_added(user_id: str, case_id: str):
    """通知收藏成功"""
    send_notification(user_id, {
        'type': 'success',
        'title': '⭐ 收藏成功',
        'message': f'案件 {case_id} 已添加到收藏',
        'data': {'case_id': case_id},
    })


def notify_favorite_removed(user_id: str, case_id: str):
    """通知取消收藏"""
    send_notification(user_id, {
        'type': 'info',
        'title': '📌 取消收藏',
        'message': f'案件 {case_id} 已从收藏移除',
        'data': {'case_id': case_id},
    })


def notify_analysis_complete(user_id: str, analysis_type: str, result: dict):
    """通知分析完成"""
    titles = {
        'sentencing': '📊 量刑分析完成',
        'defense': '⚖️ 辩护建议已生成',
        'comparison': '📋 案件对比完成',
    }
    
    send_notification(user_id, {
        'type': 'success',
        'title': titles.get(analysis_type, '分析完成'),
        'message': '点击查看详细结果',
        'data': result,
    })


def notify_search_complete(user_id: str, query: str, result_count: int):
    """通知搜索完成"""
    send_notification(user_id, {
        'type': 'info',
        'title': '🔍 搜索完成',
        'message': f'找到 {result_count} 条相关结果',
        'data': {'query': query, 'count': result_count},
    })


class NotificationType:
    """通知类型常量"""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'


if __name__ == "__main__":
    print("=== WebSocket通知模块 ===")
    print("✅ 模块已定义")
    print("\n使用方式:")
    print("  1. 在 web_app.py 中调用 init_socketio(app)")
    print("  2. 前端连接 /socket.io/")
    print("  3. 监听 'notification' 事件获取用户通知")
    print("  4. 监听 'broadcast' 事件获取系统广播")
