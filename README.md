# 福岡県連 SNSポータル

国民民主党福岡県連の議員・候補予定者のSNSアカウント一覧と、YouTube新着動画を表示する非公式試作サイトです。

- `data/people.json`：人物とアカウント一覧（2026-11-13時点のスナップショット）
- `data/posts.json`：自動更新する最新投稿
- `data/manual_posts.json`：X・Instagramなどの手動投稿
- `scripts/update_posts.py`：YouTube RSS取得と重複排除
- `.github/workflows/update.yml`：2時間ごとの収集

## 公開方法
GitHub Settings → Pages → Deploy from a branch → `main` / `(root)` → Save。

## 動作上の注意
YouTubeの公開RSS取得は失敗する場合があります。X/Instagramの自動取得は未実装です。GitHub Actionsの実行には許可設定が必要なことがあります。掲載内容は県連で確認してください。
