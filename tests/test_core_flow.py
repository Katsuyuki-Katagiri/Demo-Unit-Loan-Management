"""
基幹フロー（貸出→返却→取消）と稼働率・管理者保護の自動テスト。

各テストは conftest.py の `db` フィクスチャで用意した
一時SQLite DB上のマスタ（機種A / 個体LOT-001 / 構成品3種）に対して実行する。
"""
import datetime

import pytest

from conftest import make_check_results


# ---------- 貸出 ----------

def test_loan_normal(db):
    """全OKの貸出 → ステータス loaned・アクティブ貸出が存在する"""
    logic, dbsql = db["logic"], db["dbsql"]
    status = logic.process_loan(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    assert status == "loaned"
    assert dbsql.get_device_unit_by_id(db["unit_id"])["status"] == "loaned"
    assert dbsql.get_active_loan(db["unit_id"]) is not None


def test_loan_with_ng_creates_issue(db):
    """NG項目あり → needs_attention・Issueが1件作られる"""
    logic, dbsql = db["logic"], db["dbsql"]
    status = logic.process_loan(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"], ng_index=0),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    assert status == "needs_attention"
    assert dbsql.get_device_unit_by_id(db["unit_id"])["status"] == "needs_attention"
    assert len(dbsql.get_open_issues(db["unit_id"])) == 1


def test_loan_out_of_stock_rejected(db):
    """貸出中の個体を再度貸出しようとすると ValueError で弾かれる"""
    logic = db["logic"]
    common = dict(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    logic.process_loan(**common)  # 1回目は成功
    with pytest.raises(ValueError):
        logic.process_loan(**common)  # 2回目は在庫なしで失敗


# ---------- 返却 ----------

def _do_loan(db, ng_index=None):
    return db["logic"].process_loan(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"], ng_index=ng_index),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )


def test_return_normal(db):
    """貸出→全OK返却 → in_stock に戻り、アクティブ貸出が無くなる"""
    logic, dbsql = db["logic"], db["dbsql"]
    _do_loan(db)
    status = logic.process_return(
        device_unit_id=db["unit_id"],
        return_date="2026-07-05",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="return_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    assert status == "in_stock"
    assert dbsql.get_device_unit_by_id(db["unit_id"])["status"] == "in_stock"
    assert dbsql.get_active_loan(db["unit_id"]) is None


def test_return_with_ng_needs_attention(db):
    """返却時にNG → needs_attention・返却時Issueが作られる"""
    logic, dbsql = db["logic"], db["dbsql"]
    _do_loan(db)
    status = logic.process_return(
        device_unit_id=db["unit_id"],
        return_date="2026-07-05",
        check_results=make_check_results(db["item_ids"], ng_index=1),
        photo_dir="return_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    assert status == "needs_attention"
    assert len(dbsql.get_open_issues(db["unit_id"])) == 1


def test_return_without_loan_rejected(db):
    """アクティブ貸出が無い状態での返却は ValueError"""
    logic = db["logic"]
    with pytest.raises(ValueError):
        logic.process_return(
            device_unit_id=db["unit_id"],
            return_date="2026-07-05",
            check_results=make_check_results(db["item_ids"]),
            photo_dir="return_test",
            user_id=db["user_id"],
            user_name="管理者",
        )


# ---------- 取消（カスケード） ----------

def test_cancel_loan_cascades(db):
    """
    NG付き貸出（Issue発生）を取消 → 貸出・Issueが取消され、
    個体ステータスが in_stock に戻る
    """
    logic, dbsql = db["logic"], db["dbsql"]
    _do_loan(db, ng_index=0)
    assert dbsql.get_device_unit_by_id(db["unit_id"])["status"] == "needs_attention"

    loan = dbsql.get_loan_history(db["unit_id"])[0]
    logic.perform_cancellation(
        target_type="loan",
        target_id=loan["id"],
        user_name="管理者",
        reason="テスト取消",
        device_unit_id=db["unit_id"],
    )

    # Issueは無くなり、在庫に戻る
    assert len(dbsql.get_open_issues(db["unit_id"])) == 0
    assert dbsql.get_device_unit_by_id(db["unit_id"])["status"] == "in_stock"
    # 貸出レコード自体は canceled フラグが立つ
    assert dbsql.get_active_loan(db["unit_id"]) is None


# ---------- 稼働率 ----------

def test_utilization_full_period(db):
    """
    7/1〜7/5貸出、7/1〜7/5の期間で稼働率を計算 → 100%
    （5日中5日占有）
    """
    logic, dbsql = db["logic"], db["dbsql"]
    logic.process_loan(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    logic.process_return(
        device_unit_id=db["unit_id"],
        return_date="2026-07-05",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="return_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    rate = logic.calculate_utilization(db["unit_id"], "2026-07-01", "2026-07-05")
    assert rate == 100.0


def test_utilization_half_period(db):
    """7/1〜7/2の2日貸出を、7/1〜7/5(5日)で見ると 40%"""
    logic = db["logic"]
    logic.process_loan(
        device_unit_id=db["unit_id"],
        checkout_date="2026-07-01",
        destination="〇〇病院",
        purpose="デモ（非臨床・説明用）",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="loan_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    logic.process_return(
        device_unit_id=db["unit_id"],
        return_date="2026-07-02",
        check_results=make_check_results(db["item_ids"]),
        photo_dir="return_test",
        user_id=db["user_id"],
        user_name="管理者",
    )
    rate = logic.calculate_utilization(db["unit_id"], "2026-07-01", "2026-07-05")
    assert rate == 40.0


# ---------- 管理者保護（今回追加した安全策の回帰テスト） ----------

def test_last_admin_cannot_be_demoted(db):
    """管理者が1人だけのとき、降格は拒否される"""
    dbsql = db["dbsql"]
    admin = dbsql.get_user_by_email("admin@example.com")
    ok, _msg = dbsql.update_user_role(admin["id"], "user")
    assert ok is False
    # 権限は変わっていない
    assert dbsql.get_user_by_email("admin@example.com")["role"] == "admin"


def test_admin_demote_allowed_when_another_admin_exists(db):
    """管理者が2人いれば降格できる"""
    dbsql = db["dbsql"]
    dbsql.create_user("admin2@example.com", "管理者2", "pass", "admin")
    admin1 = dbsql.get_user_by_email("admin@example.com")
    ok, _msg = dbsql.update_user_role(admin1["id"], "user")
    assert ok is True
    assert dbsql.get_user_by_email("admin@example.com")["role"] == "user"
