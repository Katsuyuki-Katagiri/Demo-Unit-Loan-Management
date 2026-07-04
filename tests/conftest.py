"""
pytest共通設定・フィクスチャ

方針:
- テストは必ずSQLiteモードで実行する（本番Supabaseに触れない）
- そのため src を import する前に streamlit をスタブ化し、
  st.secrets.get(...) が None を返すようにして database ディスパッチャに
  SQLite を選ばせる
- 一時DBを使い、テストごとにクリーンな状態を用意する
- 通知（メール送信・スレッド起動）はテスト中は無効化する
"""
import os
import sys
import types
import tempfile
import shutil

import pytest


# --- streamlit スタブ（src import より前に sys.modules へ登録する） ---
class _Cache:
    """@st.cache_data / @st.cache_data(ttl=..) 両対応の素通しデコレータ"""
    def __call__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]

        def deco(func):
            return func
        return deco

    def clear(self):
        pass


class _Secrets(dict):
    def get(self, key, default=None):
        return None


class _StreamlitStub(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.cache_data = _Cache()
        self.cache_resource = _Cache()
        self.session_state = {}
        self.secrets = _Secrets()

    def __getattr__(self, name):
        # st.error / st.text / st.code など、その他の呼び出しは無害な no-op
        def _noop(*args, **kwargs):
            return None
        return _noop


# SUPABASE 環境変数が紛れていてもSQLiteを選ばせる
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
sys.modules["streamlit"] = _StreamlitStub()

# リポジトリルートを import パスに追加
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture()
def db(monkeypatch):
    """
    一時SQLite DBを用意し、マスタ（カテゴリ/機種/構成品/個体）を投入して返す。

    返却する辞書:
      unit_id       : 貸出対象の個体ID
      device_type_id: 機種ID
      item_ids      : 構成品IDのリスト（テンプレート順）
      category_id   : カテゴリID
      user_id       : 操作ユーザーID
    """
    import importlib
    import src.database_sqlite as dbsql

    # 一時ディレクトリにDBと写真保存先を割り当てる
    tmpdir = tempfile.mkdtemp(prefix="demoloan_test_")
    monkeypatch.setattr(dbsql, "DB_PATH", os.path.join(tmpdir, "test.db"))
    monkeypatch.setattr(dbsql, "UPLOAD_DIR", os.path.join(tmpdir, "uploads"))

    # logic 側も同じ database を参照する
    import src.logic as logic

    # 通知（スレッド起動・SMTP送信）はテスト中は無効化
    monkeypatch.setattr(logic, "trigger_issue_notification", lambda *a, **k: None)
    monkeypatch.setattr(logic, "trigger_user_notification", lambda *a, **k: None)
    monkeypatch.setattr(logic, "trigger_group_notification", lambda *a, **k: None)

    # スキーマ作成 ＋ app.py起動時と同じマイグレーション群を実行
    dbsql.init_db()
    dbsql.migrate_category_visibility()
    dbsql.migrate_loans_assetment_check()
    dbsql.migrate_loans_notes()
    dbsql.migrate_returns_assetment_check()
    dbsql.migrate_returns_notes()
    dbsql.migrate_returns_confirmation_check()

    # --- マスタ投入 ---
    # 管理者ユーザー
    dbsql.create_initial_admin("admin@example.com", "管理者", "pass")
    admin = dbsql.get_user_by_email("admin@example.com")

    # カテゴリ
    dbsql.create_category("テストカテゴリ")
    category_id = [c for c in dbsql.get_all_categories() if c["name"] == "テストカテゴリ"][0]["id"]

    # 機種
    device_type_id = dbsql.create_device_type(category_id, "機種A")

    # 構成品3種＋テンプレート（必要数 1,1,2）
    item_ids = []
    for name, qty in [("構成品1", 1), ("構成品2", 1), ("構成品3", 2)]:
        iid = dbsql.create_item(name)
        dbsql.add_template_line(device_type_id, iid, qty)
        item_ids.append(iid)

    # 個体
    dbsql.create_device_unit(device_type_id, "LOT-001")
    unit_id = dbsql.get_device_units(device_type_id)[0]["id"]

    ctx = {
        "dbsql": dbsql,
        "logic": logic,
        "unit_id": unit_id,
        "device_type_id": device_type_id,
        "item_ids": item_ids,
        "category_id": category_id,
        "user_id": admin["id"],
    }
    yield ctx

    shutil.rmtree(tmpdir, ignore_errors=True)


def make_check_results(item_ids, ng_index=None, ng_reason="紛失"):
    """
    process_loan / process_return に渡す check_results を組み立てる。
    ng_index を指定するとその構成品だけ NG にする。
    """
    qtys = {0: 1, 1: 1, 2: 2}
    results = []
    for idx, iid in enumerate(item_ids):
        is_ng = (idx == ng_index)
        results.append({
            "item_id": iid,
            "name": "構成品{}".format(idx + 1),
            "required_qty": qtys.get(idx, 1),
            "result": "NG" if is_ng else "OK",
            "ng_reason": ng_reason if is_ng else None,
            "found_qty": 0 if is_ng else None,
            "comment": "テストNG" if is_ng else None,
        })
    return results
