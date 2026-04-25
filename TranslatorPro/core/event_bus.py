"""
core/event_bus.py — Центральная шина событий (pub/sub)
Все модули эмитят сигналы сюда.
"""
from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """Центральная шина событий. Все модули эмитят сигналы сюда."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        """Подписаться на событие"""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        logger.debug(f"📡 Подписка на {event_name}")

    def emit(self, event_name: str, *args, **kwargs):
        """Эмитировать событие всем подписчикам"""
        if event_name not in self._subscribers:
            return
        for callback in self._subscribers[event_name]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события {event_name}: {e}")

    def unsubscribe(self, event_name: str, callback: Callable):
        """Отписаться от события"""
        if event_name in self._subscribers:
            self._subscribers[event_name] = [
                cb for cb in self._subscribers[event_name] if cb != callback
            ]


# Глобальный экземпляр шины событий
event_bus = EventBus()
