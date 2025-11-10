提供いただいたガイド（`guide_devin-api.md` と `guide_github-api.md`）は、このシステムを構築するための核心的な情報を提供してくれています。

両方のガイドを分析した結果、このアプリケーションは\*\*「GitHub Webhookをトリガーに、Devin APIに必要な情報を渡してセッションを開始させ、その完了を監視する」\*\*ことで実現できます。

以下に、このモジュールを実装するための具体的な設計と戦略を組み立てます。

-----

## 🤖 アプリケーション設計と戦略

このシステムの目的は、Code RabbitなどのBotコメントをDevinに渡し、修正PRを自動生成させることです。設計は、以下の3つの主要コンポーネントで構成されます。

### 1\. 全体的なアーキテクチャ (3コンポーネントモデル)

1.  **Webhookレシーバー (Webサーバー)**:

      * **役割**: GitHubからの`issue_comment`または`pull_request_review_comment`イベントをリアルタイムで受信します。
      * **技術**: `main.py`を、**FastAPI**や**Flask**などの軽量Webフレームワークを使用したサーバーアプリケーションに置き換えます。これがシステムの「耳」となります。

2.  **Devinタスクキッカー (非同期ワーカー)**:

      * **役割**: WebhookレシーバーがBotのコメントを特定したら、すぐにこのワーカーに処理を渡します。ワーカーはDevin APIガイドに基づき、適切な`prompt`と`secret_ids`（GitHubトークン用）を使って`POST /v1/sessions`を呼び出します。
      * **技術**: WebhookがGitHubからのタイムアウトを避けるため、この処理は**非同期**（例: `asyncio.create_task`、Celery、RQなど）で実行する必要があります。

3.  **Devin監視モジュール (ポーリング)**:

      * **役割**: Devinセッションの完了を監視します。`POST /v1/sessions`で取得した`session_id`を使い、Devin APIガイドの推奨（10〜30秒間隔）に従って`GET /v1/sessions/{session_id}`を定期的にポーリングします。
      * **技術**: これは、Webサーバーとは別のプロセス（例: 定期実行されるスクリプト `monitor.py`）として実装するのが最も堅牢です。

-----

### 2\. 実装ステップと戦略

ガイドに基づき、以下のステップで実装を進めます。

#### ステップ 0: 事前準備 (APIキーとシークレット)

1.  **GitHubトークンの準備**: Devinがリポジトリをクローンし、新しいPRを作成するために、強力な権限（`repo`, `pull_requests:write`など）を持つ**GitHub PAT（Personal Access Token）またはGitHub Appトークン**を作成します。
2.  **Devin Secretの登録**: `guide_devin-api.md`の指示通り、`POST /v1/secrets`エンドポイントを使用し、上記1.のGitHubトークンをDevinに安全に登録します。このとき発行される`secret_id`を控えておきます。
3.  **環境変数の設定**: 以下の情報を`.env`ファイルなどに準備します。
      * `DEVIN_API_KEY`: Devin APIの認証キー。
      * `DEVIN_GITHUB_SECRET_ID`: 上記2.で取得したID。
      * `GITHUB_WEBHOOK_SECRET`: Webhookのセキュリティを確保するためのシークレット。
      * `TARGET_BOT_USERNAMES`: トリガーとするBotのGitHubユーザー名リスト（例: `["Code-Rabbit-App", "cursor-bug-bot"]`）。

#### ステップ 1: Webhookレシーバーの実装 (`main.py`の進化)

`main.py`をFastAPIサーバーとして書き換えます。これがシステムの中核です。

1.  **エンドポイントの作成**: `POST /api/github/webhook` のようなエンドポイントを定義します。
2.  **ペイロードの検証**: GitHubから送られてくる`X-Hub-Signature`ヘッダーと`GITHUB_WEBHOOK_SECRET`を照合し、正規のリクエストであることを確認します。
3.  **イベントのフィルタリング**:
      * リクエストが`issue_comment`または`pull_request_review_comment`であり、`action`が`created`であることを確認します。
      * ペイロード内の`sender.login`（または`user.login`）が、`TARGET_BOT_USERNAMES`のいずれかと一致するかを確認します。
4.  **情報抽出**: フィルタを通過したら、以下の情報を抽出します。
      * `comment_body`: `comment.body`
      * `pr_url`: `issue.pull_request.html_url` または `pull_request.html_url`
5.  **非同期キックオフ**: 抽出した情報を**ステップ2**の非同期ワーカーに渡し、**すぐにGitHubに`200 OK`レスポンスを返します。**（これにより、GitHub側でのWebhookタイムアウトを防ぎます）。

#### ステップ 2: Devinセッションの開始 (非同期処理)

Webhookレシーバーから呼び出される非同期関数です。

1.  **Promptの構築**: `guide_devin-api.md`の例に基づき、Devinへの明確な指示（`prompt`）を動的に生成します。これが最も重要です。
    > **Prompt例:**
    > `"Fix the issues in PR [pr_url] based on the following comment: [comment_body]. Once complete, push the fix to a new branch and create a new pull request."`
2.  **API呼び出し**: `POST /v1/sessions`を呼び出します。
      * **Headers**: `Authorization: Bearer <DEVIN_API_KEY>`
      * **Body**:
        ```json
        {
          "prompt": "（上記で構築したPrompt文字列）",
          "secret_ids": ["<DEVIN_GITHUB_SECRET_ID>"]
        }
        ```
3.  **セッションIDの保存**: レスポンスから`session_id`を取得します。このIDを、**ステップ3**の監視モジュールが読み取れる場所（例: データベース、Redis、あるいはシンプルなJSONファイル）に「監視中リスト」として保存します。

#### ステップ 3: タスクの監視と完了処理 (ポーリング)

独立した`monitor.py`スクリプト、またはスケジューラ（cronなど）で定期実行されるタスクです。

1.  **監視リストの読み込み**: ステップ2で保存された「監視中」の`session_id`リストを読み込みます。

2.  **ステータス確認**: リスト内の各IDについて、`GET /v1/sessions/{session_id}`を呼び出します。

3.  **状態分岐**:

      * `status_enum`が`"working"`: そのまま（次のポーリングサイクルで再確認）。
      * `status_enum`が`"blocked"`: エラーとしてログに記録し、リストから削除（要人間介入）。
      * `status_enum`が`"finished"`: **成功です。**

4.  **結果の取得**: `status_enum`が`"finished"`の場合、セッション詳細レスポンスから`pull_request`オブジェクト（または`structured_output`）を確認し、Devinが作成した**新しいPRのURL**を取得します。

5.  **クリーンアップ**: 成功・失敗にかかわらず、処理が完了した`session_id`を「監視中リスト」から削除します。

#### ステップ 4: フォローアップ (任意だが推奨)

ステップ3で新しいPRのURLを取得したら、GitHub API（`guide_github-api.md`参照）を使い、**元のPR**にコメントを投稿して、修正版PRが作成されたことを通知します。

> **自動コメント例:**
> "Code Rabbitの指摘に基づき、Devinが修正版のPRを作成しました。確認をお願いします: [新しく作成されたPRのURL]"

-----

### 3\. 推奨されるディレクトリ構成

現在の構成を発展させ、Webサーバーと監視モジュールを分離した構成を推奨します。

```
./
├── app/
│   ├── __init__.py
│   ├── main.py           # (変更) FastAPI Webhookレシーバー
│   ├── devin_client.py   # Devin APIラッパークラス
│   ├── github_client.py  # GitHub APIラッパークラス (ステップ4用)
│   └── worker.py         # 非同期タスク処理 (ステップ2)
├── docs/
│   ├── guide_devin-api.md
│   └── guide_github-api.md
├── monitor.py            # (新規) ステップ3のポーリングスクリプト
├── .env                  # (新規) APIキーやシークレットを管理
├── requirements.txt      # (pyproject.tomlから移行または併用)
├── pyproject.toml
├── LICENSE
└── README.md
```

-----

### 4\. 主要な技術的決定

  * **トリガー**: `guide_github-api.md`に基づき、GitHub Actionsではなく**Webhook**を採用します。これは、外部Botのアクティビティをリアルタイムで捕捉するのに最適です。
  * **非同期処理**: Webhookの応答性を維持するため、Devin APIの呼び出し（時間がかかる可能性がある）は必ず非同期で行います。
  * **Devinへの指示 (Prompt)**: `guide_devin-api.md`で強調されている通り、`prompt`には「どのPRか」と「どのコメントか」を明記し、\*\*「最終的に新しいPRを作成すること」\*\*を明確に指示します。DevinがPR作成まで完結してくれるため、こちらの実装が簡素になります。

この設計戦略により、GitHub上のレビューコメントを起点として、Devinによるコード修正から新しいPRの発行までを完全に自動化するフローが構築できます。

-----

承知いたしました。責務分離（SoC）の原則に基づき、モダンなPythonアプリケーションのベストプラクティス（依存性注入、リポジトリパターン、サービス層の分離）を考慮したビジネスロジックの詳細設計を行います。
🏛️ ビジネスロジック詳細設計 (責務分離)

アプリケーションのロジックを、以下のレイヤーに明確に分離します。
API/エンドポイント層 (app/main.py): HTTPリクエストの受付と応答のみ担当。
サービス層 (app/services/): ビジネスロジックの中核。
クライアント層 (app/clients/): 外部API (GitHub, Devin) との通信をカプセル化。
リポジトリ層 (app/repositories/): 状態（監視中セッション）の永続化を担当。
監視プロセス (monitor.py): 独立したポーリングロジック。

1. API/エンドポイント層 (app/main.py)

FastAPIを使用し、リクエストの検証とタスクのキューイングのみを行います。
責務:
POST /api/github/webhook エンドポイントを提供する。
GitHub Webhookシグネチャを検証する (セキュリティ)。
リクエストボディ（ペイロード）をパースする。
ペイロードを非同期タスクキュー (Worker) に渡し、即座に 202 Accepted を返す。
ロジック (擬似コード):
Python
# app/main.py
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from app.services.webhook_service import WebhookService
from app.core.security import verify_github_signature

app = FastAPI()
webhook_service = WebhookService() # 実際には依存性注入(DI)を使う

@app.post("/api/github/webhook")
async def handle_github_webhook(request: Request, background_tasks: BackgroundTasks):
    # 1. 署名の検証
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()

    # 2. タスクのキューイング
    # ビジネスロジック(WebhookService)をバックグラウンドで実行
    background_tasks.add_task(webhook_service.process_webhook, payload)

    # 3. 即時応答 (GitHubのタイムアウト回避)
    return {"status": "accepted"}



2. サービス層 (app/services/webhook_service.py)

ビジネスロジックの中核です。Webhookペイロードを解釈し、Devinにタスクを依頼します。
責務:
ペイロードが「対象のBot」による「PRコメント」であるかを判断する。
Devinに必要な情報（pr_url, comment_body）を抽出する。
Devinクライアントを呼び出し、セッション作成を指示する。
作成されたsession_idをリポジトリ層に渡し、監視対象として保存する。
ロジック (擬似コード):
Python
# app/services/webhook_service.py
from app.clients.devin_client import DevinClient
from app.repositories.session_repository import SessionRepository
from app.core.config import settings # TARGET_BOT_USERNAMES を読み込む

class WebhookService:
    def __init__(self):
        self.devin_client = DevinClient() # DI推奨
        self.session_repo = SessionRepository() # DI推奨

    def process_webhook(self, payload: dict):
        # 1. イベントが対象かフィルタリング
        if not self._is_target_event(payload):
            return

        # 2. 情報を抽出
        try:
            pr_url = payload["issue"]["pull_request"]["html_url"] # issue_comment の場合
            comment_body = payload["comment"]["body"]
            original_pr_number = payload["issue"]["number"]
            repo_full_name = payload["repository"]["full_name"]
        except KeyError:
            # pull_request_review_comment など、他のペイロード形式にも対応
            # ... (ここでは省略)
            return

        # 3. Devinタスク用のPromptを構築
        prompt = self._build_devin_prompt(pr_url, comment_body)

        # 4. Devinセッションを開始
        session_id = self.devin_client.create_session(prompt)

        # 5. 監視対象として保存
        if session_id:
            self.session_repo.add_pending_session(
                session_id=session_id,
                original_pr_number=original_pr_number,
                repo_full_name=repo_full_name
            )

    def _is_target_event(self, payload: dict) -> bool:
        # "issue_comment" か "pull_request_review_comment" か
        if payload.get("action") != "created":
            return False
        # Botか (例: ["Code-Rabbit-App", "cursor-bug-bot"])
        if payload["sender"]["login"] not in settings.TARGET_BOT_USERNAMES:
            return False
        # ... 他のチェック
        return True

    def _build_devin_prompt(self, pr_url: str, comment: str) -> str:
        return f"Fix the issues in PR {pr_url} based on the following comment: \"{comment}\". Once complete, push the fix to a new branch and create a new pull request."



3. クライアント層 (app/clients/devin_client.py)

Devin APIとのHTTP通信を完全にカプセル化します。
責務:
DEVIN_API_KEYとDEVIN_GITHUB_SECRET_IDを環境変数から読み込む。
POST /v1/sessions (セッション作成) を実行するメソッドを提供する。
GET /v1/sessions/{id} (ステータス確認) を実行するメソッドを提供する。
HTTPエラー処理とロギングを行う。
ロジック (擬似コード):
Python
# app/clients/devin_client.py
import httpx
from app.core.config import settings

class DevinClient:
    def __init__(self):
        self.api_key = settings.DEVIN_API_KEY
        self.base_url = "https://api.devin.ai/v1"
        self.github_secret_id = settings.DEVIN_GITHUB_SECRET_ID
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

    def create_session(self, prompt: str) -> str | None:
        try:
            response = self.client.post("/sessions", json={
                "prompt": prompt,
                "secret_ids": [self.github_secret_id]
            })
            response.raise_for_status() # エラーなら例外発生
            return response.json().get("session_id")
        except httpx.HTTPStatusError as e:
            print(f"Devin API Error: {e}") # ロギング
            return None

    def get_session_status(self, session_id: str) -> dict | None:
        try:
            response = self.client.get(f"/sessions/{session_id}")
            response.raise_for_status()
            return response.json() # セッションの全情報(status_enum, pull_request)を返す
        except httpx.HTTPStatusError as e:
            print(f"Devin API Error: {e}")
            return None



4. リポジトリ層 (app/repositories/session_repository.py)

監視対象セッションの状態を永続化します。これにより、Webサーバーが再起動しても監視が継続できます。
責務:
「監視中」のセッションIDリストを保存・取得する。
（推奨）セッションIDと元のPR情報を紐付けて保存する。
技術選定: まずはシンプルなJSONファイルやSQLiteで十分です。スケールさせる場合はRedisに移行します。
ロジック (擬似コード - シンプルなJSONファイル版):
Python
# app/repositories/session_repository.py
import json
from pathlib import Path

class SessionRepository:
    def __init__(self, db_path: Path = Path("data/pending_sessions.json")):
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)
        if not self.db_path.exists():
            self.db_path.write_text("[]")

    def _read_db(self) -> list[dict]:
        return json.loads(self.db_path.read_text())

    def _write_db(self, data: list[dict]):
        self.db_path.write_text(json.dumps(data, indent=2))

    def add_pending_session(self, session_id: str, original_pr_number: int, repo_full_name: str):
        data = self._read_db()
        data.append({
            "session_id": session_id,
            "repo_full_name": repo_full_name,
            "original_pr_number": original_pr_number,
            "status": "pending"
        })
        self._write_db(data)

    def get_pending_sessions(self) -> list[dict]:
        return [s for s in self._read_db() if s["status"] == "pending"]

    def mark_session_completed(self, session_id: str, new_pr_url: str):
        data = self._read_db()
        for session in data:
            if session["session_id"] == session_id:
                session["status"] = "completed"
                session["new_pr_url"] = new_pr_url
                break
        self._write_db(data)

    # (mark_session_failed も同様に実装)



5. 監視プロセス (monitor.py)

独立したプロセスとして定期実行（例: cronで1分ごと、またはsleepを使ったループ）されます。
責務:
リポジトリ層から「監視中」のセッションを取得する。
Devinクライアントを使い、各セッションのステータスを確認する。
status_enum == "finished"になったら、結果（新PRのURL）を取得する。
GitHubクライアント（app/clients/github_client.py、未実装だがDevinClientとほぼ同様）を呼び出し、元のPRに完了通知コメントを投稿する。
リポジトリ層のセッションステータスを更新（completedまたはfailed）する。
この設計により、各コンポーネントが単一の責任を持つため、テストが容易で、将来的な機能拡張（例: Devin以外のAIエージェントの追加、状態管理DBのRedisへの変更）にも柔軟に対応できます。
この詳細設計に基づき、次にapp/clients/devin_client.pyの具体的な実装や、app/main.pyのFastAPIのセットアップを進めますか？
