# Supabase Storage Helper Functions
# 写真をSupabase Storageにアップロード・取得するためのヘルパー関数

import os
import uuid
from typing import Optional
import streamlit as st

def get_storage_client():
    """Supabase Storageクライアントを取得"""
    from src.database_supabase import get_client
    return get_client().storage

def upload_photo(bucket: str, file_data: bytes, filename: str, content_type: str = "image/webp") -> Optional[str]:
    """
    写真をSupabase Storageにアップロード
    
    Args:
        bucket: バケット名（'items', 'sessions'）
        file_data: ファイルのバイトデータ
        filename: 保存するファイル名（パス含む）
        content_type: MIMEタイプ
    
    Returns:
        成功時: ファイルパス、失敗時: None
    """
    try:
        storage = get_storage_client()
        
        # アップロード
        result = storage.from_(bucket).upload(
            path=filename,
            file=file_data,
            file_options={"content-type": content_type}
        )
        
        return filename
    except Exception as e:
        # バケットが存在しない場合は作成を試みる
        print(f"Storage upload error: {e}")
        return None

def get_photo_url(bucket: str, filepath: str) -> Optional[str]:
    """
    Supabase Storageの写真URLを取得
    
    Args:
        bucket: バケット名
        filepath: ファイルパス
    
    Returns:
        公開URL
    """
    try:
        storage = get_storage_client()
        # 公開URLを取得（署名付き）
        result = storage.from_(bucket).create_signed_url(filepath, 3600)  # 1時間有効
        return result.get("signedURL")
    except Exception as e:
        print(f"Get URL error: {e}")
        return None

def delete_photo(bucket: str, filepath: str) -> bool:
    """
    Supabase Storageの写真を削除
    
    Args:
        bucket: バケット名
        filepath: ファイルパス
    
    Returns:
        成功: True, 失敗: False
    """
    try:
        storage = get_storage_client()
        storage.from_(bucket).remove([filepath])
        return True
    except Exception as e:
        print(f"Delete error: {e}")
        return False

def list_photos(bucket: str, folder: str) -> list:
    """
    フォルダ内の写真一覧を取得
    
    Args:
        bucket: バケット名
        folder: フォルダパス
    
    Returns:
        ファイル一覧
    """
    try:
        storage = get_storage_client()
        result = storage.from_(bucket).list(folder)
        return result
    except Exception as e:
        print(f"List error: {e}")
        return []

# --- 高レベルヘルパー関数 ---

def upload_item_photo(item_id: int, file_data: bytes, extension: str = "webp") -> Optional[str]:
    """
    構成品の写真をアップロード
    
    Args:
        item_id: 構成品ID
        file_data: ファイルデータ
        extension: ファイル拡張子
    
    Returns:
        ファイルパス
    """
    filename = f"items/item_{item_id}.{extension}"
    return upload_photo("items", file_data, filename)

def upload_session_photo(session_id: int, file_data: bytes, photo_index: int, extension: str = "webp") -> Optional[str]:
    """
    貸出・返却セッションの写真をアップロード
    
    Args:
        session_id: チェックセッションID
        file_data: ファイルデータ
        photo_index: 写真のインデックス（0, 1, 2...）
        extension: ファイル拡張子
    
    Returns:
        ファイルパス
    """
    filename = f"sessions/{session_id}/photo_{photo_index}.{extension}"
    return upload_photo("sessions", file_data, filename)

def get_item_photo_url(item_id: int, extension: str = "webp") -> Optional[str]:
    """
    構成品の写真URLを取得
    """
    filename = f"items/item_{item_id}.{extension}"
    return get_photo_url("items", filename)

def get_session_photos(session_id: int) -> list:
    """
    セッションの全写真URLを取得
    """
    folder = f"sessions/{session_id}"
    files = list_photos("sessions", folder)
    
    urls = []
    for f in files:
        if f.get("name"):
            filepath = f"{folder}/{f['name']}"
            url = get_photo_url("sessions", filepath)
            if url:
                urls.append(url)
    
    return urls

# --- Supabase使用チェック ---

def is_supabase_storage_enabled() -> bool:
    """
    Supabase Storageが有効かどうかを確認
    """
    try:
        supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
        return bool(supabase_url and supabase_key)
    except Exception:
        return False
