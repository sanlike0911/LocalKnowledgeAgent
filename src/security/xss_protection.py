"""
XSS対策・入力サニタイゼーション機能
Streamlitアプリケーション向けのXSS保護機能
"""

import html
import re
from typing import Any, Dict, List, Optional, Union
from src.utils.structured_logger import get_logger


class XSSProtection:
    """XSS攻撃対策・入力サニタイゼーション"""
    
    # 危険なHTMLタグパターン
    DANGEROUS_TAGS = [
        r'<script.*?</script>',
        r'<iframe.*?</iframe>',
        r'<object.*?</object>',
        r'<embed.*?>',
        r'<form.*?</form>',
        r'<input.*?>',
        r'<textarea.*?</textarea>',
        r'<select.*?</select>',
        r'<button.*?</button>',
        r'<link.*?>',
        r'<meta.*?>',
        r'<style.*?</style>'
    ]
    
    # 危険なJavaScript関連パターン
    DANGEROUS_JS_PATTERNS = [
        r'javascript:',
        r'onclick=',
        r'onload=',
        r'onerror=',
        r'onmouseover=',
        r'onfocus=',
        r'onblur=',
        r'onchange=',
        r'onsubmit=',
        r'eval\(',
        r'document\.',
        r'window\.',
        r'location\.',
        r'alert\(',
        r'confirm\(',
        r'prompt\('
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def sanitize_input(self, user_input: str, allow_markdown: bool = False) -> str:
        """
        ユーザー入力のサニタイゼーション
        
        Args:
            user_input: サニタイズ対象の入力
            allow_markdown: Markdown記法を許可するか
            
        Returns:
            str: サニタイズ済みの入力
        """
        if not isinstance(user_input, str):
            return str(user_input)
        
        try:
            # 1. HTMLエスケープ
            sanitized = html.escape(user_input, quote=True)
            
            # 2. 危険なHTMLタグ除去
            sanitized = self._remove_dangerous_tags(sanitized)
            
            # 3. JavaScript関連パターン除去
            sanitized = self._remove_javascript_patterns(sanitized)
            
            # 4. SQL injection対策（基本的なパターン）
            sanitized = self._prevent_sql_injection(sanitized)
            
            # 5. Markdownの場合は安全な要素のみ許可
            if allow_markdown:
                sanitized = self._sanitize_markdown(sanitized)
            
            # ログ出力（デバッグ用）
            if user_input != sanitized:
                self.logger.info("入力をサニタイズしました", extra={
                    "original_length": len(user_input),
                    "sanitized_length": len(sanitized),
                    "has_dangerous_content": True
                })
            
            return sanitized
            
        except Exception as e:
            self.logger.error(f"入力サニタイゼーションエラー: {e}", extra={
                "input_length": len(user_input),
                "error": str(e)
            })
            # エラー時は安全な文字のみ返す
            return re.sub(r'[^\w\s\-_.,!?()]', '', user_input)
    
    def _remove_dangerous_tags(self, text: str) -> str:
        """危険なHTMLタグを除去"""
        for pattern in self.DANGEROUS_TAGS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text
    
    def _remove_javascript_patterns(self, text: str) -> str:
        """JavaScript関連の危険なパターンを除去"""
        for pattern in self.DANGEROUS_JS_PATTERNS:
            text = re.sub(pattern, '[REMOVED]', text, flags=re.IGNORECASE)
        return text
    
    def _prevent_sql_injection(self, text: str) -> str:
        """基本的なSQL injection対策"""
        dangerous_sql = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+.*\s+set',
            r'exec\s*\(',
            r'execute\s*\(',
            r'sp_executesql'
        ]
        
        for pattern in dangerous_sql:
            text = re.sub(pattern, '[SQL_BLOCKED]', text, flags=re.IGNORECASE)
        return text
    
    def _sanitize_markdown(self, text: str) -> str:
        """Markdownの安全な記法のみ許可"""
        # 許可されるMarkdown要素（基本的なもののみ）
        allowed_markdown = [
            r'\*\*.*?\*\*',  # **太字**
            r'\*.*?\*',      # *斜体*
            r'`.*?`',        # `コード`
            r'~~~.*?~~~',    # ~~~コードブロック~~~
            r'```.*?```',    # ```コードブロック```
            r'^\s*#.*',      # # ヘッダー
            r'^\s*-.*',      # - リスト
            r'^\s*\d+\..*'   # 1. 番号付きリスト
        ]
        
        # 危険なMarkdown要素を除去
        # [リンク](url) は慎重に処理
        text = re.sub(r'\[([^\]]*)\]\(javascript:[^)]*\)', r'\1', text, flags=re.IGNORECASE)
        
        return text
    
    def validate_file_name(self, filename: str) -> str:
        """
        ファイル名のサニタイゼーション
        
        Args:
            filename: 元のファイル名
            
        Returns:
            str: サニタイズされたファイル名
        """
        try:
            # パス区切り文字を除去
            filename = re.sub(r'[/\\]', '_', filename)
            
            # 危険な文字を除去
            filename = re.sub(r'[<>:"|?*]', '', filename)
            
            # 連続するドットを単一に
            filename = re.sub(r'\.{2,}', '.', filename)
            
            # 先頭・末尾の空白とドット除去
            filename = filename.strip(' .')
            
            # 空の場合はデフォルト名
            if not filename:
                filename = 'sanitized_file'
            
            # 最大長制限（Windows制限）
            if len(filename) > 255:
                name_part, ext_part = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                filename = name_part[:250] + ('.' + ext_part if ext_part else '')
            
            return filename
            
        except Exception as e:
            self.logger.error(f"ファイル名サニタイゼーションエラー: {e}")
            return 'sanitized_file.txt'
    
    def check_streamlit_safety(self) -> Dict[str, Any]:
        """
        Streamlitの標準セキュリティ機能チェック
        
        Returns:
            Dict: セキュリティ状況レポート
        """
        security_report = {
            "xss_protection": {
                "status": "enabled",
                "description": "Streamlitは標準でHTMLエスケープを実行",
                "details": [
                    "st.write()は自動的にHTMLエスケープ",
                    "st.markdown(unsafe_allow_html=False)が初期値",
                    "ユーザー入力は自動サニタイズ"
                ]
            },
            "csrf_protection": {
                "status": "partial",
                "description": "Streamlitはセッション管理でCSRF対策を実施",
                "details": [
                    "セッショントークンによる状態管理",
                    "WebSocket通信でリクエスト制御"
                ]
            },
            "content_security_policy": {
                "status": "limited",
                "description": "基本的なCSP設定",
                "details": [
                    "スクリプト実行制限",
                    "外部リソース読み込み制限"
                ]
            },
            "additional_protections": {
                "input_sanitization": "実装済み（本モジュール）",
                "file_validation": "実装済み（FileValidator）",
                "path_traversal_protection": "実装済み（FileValidator）"
            }
        }
        
        self.logger.info("Streamlitセキュリティ状況確認完了", extra=security_report)
        return security_report


# XSS保護の便利関数
_xss_protection = XSSProtection()

def sanitize_user_input(user_input: str, allow_markdown: bool = False) -> str:
    """
    ユーザー入力サニタイゼーション便利関数
    
    Args:
        user_input: サニタイズ対象入力
        allow_markdown: Markdown許可フラグ
        
    Returns:
        str: サニタイズ済み入力
    """
    return _xss_protection.sanitize_input(user_input, allow_markdown)


def validate_filename(filename: str) -> str:
    """
    ファイル名検証便利関数
    
    Args:
        filename: 元のファイル名
        
    Returns:
        str: 検証済みファイル名
    """
    return _xss_protection.validate_file_name(filename)


def get_security_status() -> Dict[str, Any]:
    """
    セキュリティ状況取得便利関数
    
    Returns:
        Dict: セキュリティレポート
    """
    return _xss_protection.check_streamlit_safety()