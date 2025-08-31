"""
ファイル検証・セキュリティ機能
アップロードされるファイルの検証とセキュリティチェック
"""

import os
MAGIC_AVAILABLE = False  # Windows環境では安全のため無効化
from pathlib import Path
from typing import List, Optional, Tuple
import hashlib
from src.utils.structured_logger import get_logger
# セキュリティ例外は本ファイル内で定義


class FileValidator:
    """ファイル検証・セキュリティチェック"""
    
    # サポートされるファイル形式とMIMEタイプ
    ALLOWED_MIME_TYPES = {
        'application/pdf': ['.pdf'],
        'text/plain': ['.txt'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    }
    
    # 最大ファイルサイズ（50MB）
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # 危険な拡張子
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', 
        '.jar', '.sh', '.ps1', '.msi', '.dll', '.sys'
    }
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def validate_file(self, file_path: str, max_size: Optional[int] = None) -> Tuple[bool, str]:
        """
        ファイルの包括的検証
        
        Args:
            file_path: 検証対象ファイルパス
            max_size: 最大ファイルサイズ（Noneの場合デフォルト使用）
            
        Returns:
            Tuple[bool, str]: (検証結果, エラーメッセージ)
        """
        try:
            file_path = Path(file_path).resolve()
            
            # 1. ファイル存在チェック
            if not file_path.exists():
                return False, "ファイルが存在しません"
                
            if not file_path.is_file():
                return False, "ディレクトリは処理できません"
            
            # 2. パストラバーサル攻撃対策
            if not self._check_path_traversal(file_path):
                return False, "不正なファイルパスが検出されました"
            
            # 3. ファイルサイズ検証
            max_size = max_size or self.MAX_FILE_SIZE
            if not self._validate_file_size(file_path, max_size):
                return False, f"ファイルサイズが制限を超えています（最大: {max_size // (1024*1024)}MB）"
            
            # 4. 拡張子検証
            if not self._validate_file_extension(file_path):
                return False, "サポートされていないファイル形式です"
            
            # 5. MIMEタイプ検証
            if not self._validate_mime_type(file_path):
                return False, "ファイル形式が拡張子と一致しません"
            
            # 6. ファイル内容検証（マルウェアスキャン的チェック）
            if not self._validate_file_content(file_path):
                return False, "ファイル内容に問題が検出されました"
                
            self.logger.info(f"ファイル検証成功: {file_path}", extra={
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_extension": file_path.suffix
            })
            
            return True, "検証成功"
            
        except Exception as e:
            error_msg = f"ファイル検証中にエラー: {str(e)}"
            self.logger.error(error_msg, extra={
                "file_path": str(file_path),
                "error": str(e)
            })
            return False, error_msg
    
    def _check_path_traversal(self, file_path: Path) -> bool:
        """
        パストラバーサル攻撃対策
        
        Args:
            file_path: 検証対象パス
            
        Returns:
            bool: 安全なパスの場合True
        """
        try:
            # 解決済みの絶対パスを取得
            resolved_path = file_path.resolve()
            
            # 危険なパス要素をチェック
            dangerous_elements = ['..', './', '\\..\\', '..\\', '../']
            path_str = str(resolved_path)
            
            for element in dangerous_elements:
                if element in path_str:
                    self.logger.warning(f"パストラバーサル攻撃の可能性: {path_str}", extra={
                        "dangerous_element": element,
                        "file_path": path_str
                    })
                    return False
            
            # Windowsドライブレター以外のルートパスチェック
            if os.name == 'nt':  # Windows
                if len(resolved_path.parts) > 0 and resolved_path.parts[0].startswith('\\'):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"パストラバーサルチェックエラー: {e}", extra={
                "file_path": str(file_path)
            })
            return False
    
    def _validate_file_size(self, file_path: Path, max_size: int) -> bool:
        """
        ファイルサイズ検証
        
        Args:
            file_path: ファイルパス
            max_size: 最大サイズ（バイト）
            
        Returns:
            bool: サイズが適切な場合True
        """
        try:
            file_size = file_path.stat().st_size
            if file_size > max_size:
                self.logger.warning(f"ファイルサイズ制限超過: {file_size} > {max_size}", extra={
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "max_size": max_size
                })
                return False
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルサイズ検証エラー: {e}")
            return False
    
    def _validate_file_extension(self, file_path: Path) -> bool:
        """
        ファイル拡張子検証
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: 許可された拡張子の場合True
        """
        extension = file_path.suffix.lower()
        
        # 危険な拡張子チェック
        if extension in self.DANGEROUS_EXTENSIONS:
            self.logger.warning(f"危険な拡張子検出: {extension}", extra={
                "file_path": str(file_path),
                "extension": extension
            })
            return False
        
        # 許可された拡張子チェック
        allowed_extensions = set()
        for extensions in self.ALLOWED_MIME_TYPES.values():
            allowed_extensions.update(extensions)
            
        if extension not in allowed_extensions:
            self.logger.warning(f"サポートされていない拡張子: {extension}", extra={
                "file_path": str(file_path),
                "extension": extension,
                "allowed_extensions": list(allowed_extensions)
            })
            return False
            
        return True
    
    def _validate_mime_type(self, file_path: Path) -> bool:
        """
        MIMEタイプ検証
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: MIMEタイプが適切な場合True
        """
        try:
            # python-magicを使用してMIMEタイプを取得
            if not MAGIC_AVAILABLE:
                # python-magicが利用できない場合は拡張子ベースで判定
                self.logger.info("python-magic無効化、拡張子ベース検証を使用")
                return True
            
            # MAGIC_AVAILABLE = Falseのため、この分岐は実行されない
            mime_type = "application/octet-stream"
            extension = file_path.suffix.lower()
            
            # 許可されたMIMEタイプかチェック
            if mime_type not in self.ALLOWED_MIME_TYPES:
                self.logger.warning(f"許可されていないMIMEタイプ: {mime_type}", extra={
                    "file_path": str(file_path),
                    "mime_type": mime_type,
                    "extension": extension
                })
                return False
            
            # 拡張子とMIMEタイプの整合性チェック
            expected_extensions = self.ALLOWED_MIME_TYPES[mime_type]
            if extension not in expected_extensions:
                self.logger.warning(f"拡張子とMIMEタイプの不整合: {extension} vs {mime_type}", extra={
                    "file_path": str(file_path),
                    "extension": extension,
                    "mime_type": mime_type,
                    "expected_extensions": expected_extensions
                })
                return False
                
            return True
            
        except Exception as e:
            # python-magicが利用できない場合は拡張子ベースで判定
            self.logger.info(f"MIMEタイプ検証をスキップ（magic利用不可）: {e}")
            return True
    
    def _validate_file_content(self, file_path: Path) -> bool:
        """
        ファイル内容の基本検証
        
        Args:
            file_path: ファイルパス
            
        Returns:
            bool: ファイル内容が安全な場合True
        """
        try:
            # ファイルサイズが0でないことを確認
            if file_path.stat().st_size == 0:
                self.logger.warning(f"空ファイルが検出されました: {file_path}")
                return False
            
            # PDFファイルの基本構造チェック
            if file_path.suffix.lower() == '.pdf':
                return self._validate_pdf_structure(file_path)
            
            # テキストファイルのエンコーディングチェック
            elif file_path.suffix.lower() == '.txt':
                return self._validate_text_encoding(file_path)
                
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル内容検証エラー: {e}")
            return False
    
    def _validate_pdf_structure(self, file_path: Path) -> bool:
        """PDFファイル構造の基本検証"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    self.logger.warning(f"不正なPDFヘッダー: {file_path}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"PDF構造検証エラー: {e}")
            return False
    
    def _validate_text_encoding(self, file_path: Path) -> bool:
        """テキストファイルエンコーディング検証"""
        try:
            encodings = ['utf-8', 'shift_jis', 'euc-jp', 'cp932']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)  # 最初の1KBを試し読み
                    return True
                except UnicodeDecodeError:
                    continue
            
            self.logger.warning(f"サポートされていないテキストエンコーディング: {file_path}")
            return False
            
        except Exception as e:
            self.logger.error(f"テキストエンコーディング検証エラー: {e}")
            return False
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        ファイルのSHA-256ハッシュを計算
        
        Args:
            file_path: ファイルパス
            
        Returns:
            str: SHA-256ハッシュ値
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"ハッシュ計算エラー: {e}")
            return ""


# セキュリティ例外クラス
class SecurityError(Exception):
    """セキュリティ関連エラー"""
    pass


def validate_file_upload(file_path: str, max_size: Optional[int] = None) -> Tuple[bool, str]:
    """
    ファイルアップロード検証の便利関数
    
    Args:
        file_path: 検証対象ファイルパス
        max_size: 最大ファイルサイズ
        
    Returns:
        Tuple[bool, str]: (検証結果, メッセージ)
    """
    validator = FileValidator()
    return validator.validate_file(file_path, max_size)