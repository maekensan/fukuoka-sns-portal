# 福岡県連 SNSポータル

公開サイト: https://maekensan.github.io/fukuoka-sns-portal/

## 取得できる投稿
- **YouTube**: RSS取得を試みます。GitHub Secretsに `YOUTUBE_API_KEY` を登録すると、公式YouTube Data API v3で取得します（推奨）。
- **X**: 投稿読み取りAPIは従量課金。月額0円運用では自動取得しません。
- **Instagram**: Business Discoveryの取得コードを実装済み。対応するMetaビジネスアカウント／アクセストークンがない間は自動取得を行いません。個人アカウントは対象外です。
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

## Instagramの自動取得設定（任意・上級）

Meta for Developersでアプリを作成し、Facebookログイン型のInstagram Graph API / Business Discoveryを利用できるInstagramビジネスアカウントと、適切な権限・アクセストークンを取得する必要があります。アプリモード、審査、アカウント種別によっては取得不可です。

- GitHub Actions Secretsに `META_IG_USER_ID`（取得元InstagramビジネスアカウントのID）
- GitHub Actions Secretsに `META_ACCESS_TOKEN`（権限のあるトークン）

を登録すると、`scripts/update_instagram.py` が既存のアカウント一覧のInstagram URLを対象にBusiness Discoveryを試行します。シークレット未設定なら処理をスキップします。

※ この方式は **32人の投稿を無条件に取得できるものではありません**。事前に権限と対応アカウントの確認が必要です。Xは無料の公式読み取り手段がないため未実装です。認証情報をGitHubの通常ファイルやチャットに貼らないでください。
