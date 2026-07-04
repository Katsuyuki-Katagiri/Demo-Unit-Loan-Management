-- Supabase Storage バケット設定
-- このスクリプトをSupabaseダッシュボードの「SQL Editor」で実行してください

-- Storage バケットを作成
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('items', 'items', true),
  ('sessions', 'sessions', true)
ON CONFLICT (id) DO NOTHING;

-- items バケットのアクセスポリシー
CREATE POLICY "Allow all access to items bucket"
ON storage.objects FOR ALL
USING (bucket_id = 'items');

-- sessions バケットのアクセスポリシー
CREATE POLICY "Allow all access to sessions bucket"
ON storage.objects FOR ALL
USING (bucket_id = 'sessions');
