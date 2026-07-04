# Supabase セットアップガイド

このドキュメントでは、デモ機管理アプリをSupabaseに移行する手順を説明します。

## 1. Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com) にアクセスしてアカウントを作成
2. 「New Project」をクリック
3. プロジェクト名を入力（例：`demo-unit-loan`）
4. パスワードを設定（任意の強力なパスワード）
5. リージョンを選択（例：Tokyo）
6. 「Create new project」をクリック

## 2. データベーステーブルの作成

1. Supabaseダッシュボードで「SQL Editor」を開く
2. `scripts/supabase_schema.sql` の内容をコピー&ペースト
3. 「Run」をクリックして実行
4. 全テーブルが作成されることを確認

## 3. API キーの取得

1. Supabaseダッシュボードで「Settings」→「API」を開く
2. 以下の情報をメモ：
   - **Project URL**: `https://xxx.supabase.co` 形式
   - **service_role key**: `eyJ...` 形式（秘密鍵）

> ⚠️ **重要**: service_role キーは秘密です。公開しないでください。

## 4. Streamlit Cloudの設定

1. Streamlit Cloudで対象アプリを開く
2. 「Settings」→「Secrets」を開く
3. 以下を追加：

```toml
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
```

4. 「Save」をクリック
5. アプリを再起動

## 5. 動作確認

1. アプリにアクセス
2. 初回アクセス時に管理者アカウントを作成
3. ログインして機能を確認

## トラブルシューティング

### エラー: "SUPABASE_URL と SUPABASE_KEY が設定されていません"
- Streamlit CloudのSecretsに正しく設定されているか確認

### エラー: "relation does not exist"
- SQL Editorでスキーマを再実行

### データが保存されない
- service_role キーを使用しているか確認（anon キーではダメ）
