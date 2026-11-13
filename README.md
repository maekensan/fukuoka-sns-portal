# 福岡県連 SNSポータル

公開サイト: https://maekensan.github.io/fukuoka-sns-portal/

## 取得できる投稿
- **YouTube**: RSS取得を試みます。GitHub Secretsに `YOUTUBE_API_KEY` を登録すると、公式YouTube Data API v3で取得します（推奨）。
- **X**: 投稿読み取りAPIは従量課金。月額0円運用では自動取得しません。
- **Instagram**: プロアカウントとMetaアプリの認証・権限が整えばBusiness Discovery経由の取得を別途実装可能。現状は未実装です。
- **その他**: `data/manual_posts.json` で投稿URLを登録します。

## YouTube APIキーの設定（キーは公開しない）
1. Google Cloud Consoleでプロジェクトを作り、YouTube Data API v3を有効にする。
2. [認証情報] → [認証情報を作成] → [APIキー]。キーにYouTube Data API v3のAPI制限をかける。
3. GitHubの本リポジトリ → Settings → Secrets and variables → Actions → New repository secret。
4. Name: `YOUTUBE_API_KEY` / Secret: 発行されたキー。
5. Actions → Update YouTube posts → Run workflow を実行。
6. `data/status.json` で `youtubeFeedsSucceeded` と `errors` を確認する。

APIキーはGitHubファイル、README、チャット、公開URLに直接貼らないでください。無料クォータを超えないこと、課金が有効になっていないことをCloud Consoleで確認してください。

## 更新頻度
GitHub Actionsで2時間ごとに収集します（遅延・欠落の可能性あり）。
成功した既存データは取得失敗時も保持されます。

## 管理
- `data/people.json`: 人物・SNSの公開用スナップショット
- `data/posts.json`: GitHub Actionsが更新する投稿データ
- `data/manual_posts.json`: その他SNSの手動投稿
- `data/excluded_names.json`: 一時的に非公開にする人物名
- `data/status.json`: 最終実行結果

人物名やSNS URLは元のGoogleスプレッドシートと現状は自動同期していません。変更時にはGitHub側への反映も必要です。
