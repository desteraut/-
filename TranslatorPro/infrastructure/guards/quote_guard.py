"""
QuoteGuard — защита и балансировка кавычек
"""


class QuoteGuard:
    """Управление кавычками в тексте"""
    
    def __init__(self):
        self.quote_chars = ['"', "'", '"', '"']
    
    def count_quotes(self, text: str) -> int:
        """Считает количество кавычек"""
        return text.count('"')
    
    def is_balanced(self, text: str) -> bool:
        """Проверяет баланс кавычек"""
        return self.count_quotes(text) % 2 == 0
    
    def escape_for_renpy(self, text: str) -> str:
        """Экранирует кавычки для Ren'Py"""
        return text.replace('"', '\\"')
    
    def validate(self, original: str, translated: str) -> dict:
        """Проверяет кавычки после перевода"""
        issues = []
        
        if not self.is_balanced(translated):
            issues.append("unclosed_quotes")
        
        if self.count_quotes(original) != self.count_quotes(translated):
            issues.append("quote_count_mismatch")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }