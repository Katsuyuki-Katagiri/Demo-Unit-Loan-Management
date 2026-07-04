-- Supabase Storage バケット / ポリシー設定
-- このスクリプトをSupabaseダッシュボードの「SQL Editor」で実行してください
-- アプリは以下のバケット名を使用します（src/database_supabase.py と一致させること）:
--   item-photos    … 構成品マスタの写真
--   session-photos … 貸出・返却時のセッション写真

-- 1. Storage バケットを作成（公開・再実行しても安全）
INSERT INTO storage.buckets (id, name, public)
VALUES
  ('item-photos', 'item-photos', true),
  ('session-photos', 'session-photos', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- 2. アクセスポリシー
-- アプリは anon キーで接続し、写真の参照・アップロードを行うため、
-- anon ロールに両バケットへのフルアクセスを許可する。
DROP POLICY IF EXISTS "item_photos_anon_all" ON storage.objects;
DROP POLICY IF EXISTS "session_photos_anon_all" ON storage.objects;

CREATE POLICY "item_photos_anon_all" ON storage.objects
  FOR ALL TO anon
  USING (bucket_id = 'item-photos')
  WITH CHECK (bucket_id = 'item-photos');

CREATE POLICY "session_photos_anon_all" ON storage.objects
  FOR ALL TO anon
  USING (bucket_id = 'session-photos')
  WITH CHECK (bucket_id = 'session-photos');
