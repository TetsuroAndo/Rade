# 開発経過ドキュメント

このドキュメントは、Radeプロジェクトの開発経過を記録します。

## プロジェクト概要

GitHub Webhookをトリガーに、Devin APIを使用してコードレビューコメントに基づく修正PRを自動生成するシステム。

## 開発ステータス

### ✅ 完了したタスク

- [x] 設計書の作成 (`docs/design.md`)
- [x] プロジェクト構造の作成と依存関係の設定
- [x] コアモジュールの実装
- [x] クライアント層の実装
- [x] リポジトリ層の実装
- [x] サービス層の実装
- [x] API層の実装
- [x] 監視プロセスの実装
- [x] 環境変数テンプレートの作成 (`.env.example`)
- [x] カスタム例外クラスの実装 (`app/core/exceptions.py`)
- [x] ロギング設定の改善 (`app/core/logging_config.py`)
- [x] エラーハンドリングの強化（全レイヤー）
- [x] ユニットテストの作成（pytest）

### 🔄 進行中のタスク

- [ ] 統合テストの作成
- [ ] デプロイ設定
- [ ] ドキュメントの整備（API仕様書など）
- [ ] パフォーマンス最適化

### ⏳ 未着手のタスク

- [ ] E2Eテストの作成
- [ ] CI/CDパイプラインの設定
- [ ] メトリクス収集（Prometheus等）
- [ ] エラーレポート機能（Sentry等）

## 実装詳細

### プロジェクト構造

```
./
├── app/
│   ├── __init__.py
│   ├── main.py           # ✅ FastAPI Webhookレシーバー
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py     # ✅ 設定管理
│   │   └── security.py   # ✅ セキュリティ（署名検証）
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── devin_client.py   # ✅ Devin APIラッパー
│   │   └── github_client.py  # ✅ GitHub APIラッパー
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── session_repository.py  # ✅ セッション状態管理
│   └── services/
│       ├── __init__.py
│       └── webhook_service.py  # ✅ Webhook処理ロジック
├── monitor.py            # ✅ 監視スクリプト
├── .env.example          # ✅ 環境変数の例
├── data/                 # ✅ セッション状態保存ディレクトリ
├── pyproject.toml        # ✅ 依存関係定義
├── tests/                # ✅ テストスイート
│   ├── __init__.py
│   ├── test_exceptions.py
│   ├── test_security.py
│   ├── test_devin_client.py
│   ├── test_github_client.py
│   ├── test_session_repository.py
│   └── test_webhook_service.py
└── docs/
    ├── design.md         # ✅ 設計書
    ├── development.md    # ✅ このファイル
    ├── guide_devin-api.md
    └── guide_github-api.md
```

## 実装ログ

### 2024年 - プロジェクト開始

#### フェーズ1: プロジェクト基盤の構築

**ステータス**: ✅ 完了

- [x] 設計書の作成とレビュー (`docs/design.md`)
- [x] プロジェクト構造の作成
- [x] 依存関係の定義 (`pyproject.toml`)
- [x] 環境変数テンプレートの作成 (`.env.example`)

**実装内容**:
- `pyproject.toml`に必要な依存関係（FastAPI、httpx、pydantic-settings等）を定義
- `.env.example`に環境変数のテンプレートを作成

#### フェーズ2: コアモジュールの実装

**ステータス**: ✅ 完了

- [x] `app/core/config.py` - 設定管理
- [x] `app/core/security.py` - GitHub Webhook署名検証

**実装内容**:
- **config.py**: Pydantic Settingsを使用した設定管理クラスを実装
  - Devin API設定（APIキー、Secret ID、ベースURL）
  - GitHub設定（Webhookシークレット、トークン、対象Botユーザー名）
  - リポジトリ設定（セッションDBパス）
  - 監視設定（ポーリング間隔）
- **security.py**: GitHub Webhook署名検証機能を実装
  - HMAC SHA-256を使用した署名検証
  - タイミング攻撃を防ぐための定数時間比較を実装

#### フェーズ3: クライアント層の実装

**ステータス**: ✅ 完了

- [x] `app/clients/devin_client.py` - Devin APIクライアント
- [x] `app/clients/github_client.py` - GitHub APIクライアント

**実装内容**:
- **devin_client.py**: Devin APIとの通信をカプセル化
  - `create_session()`: セッション作成メソッド（非同期）
  - `get_session_status()`: セッション状態取得メソッド（非同期）
  - エラーハンドリングとロギングを実装
  - httpx.AsyncClientを使用した非同期HTTP通信
- **github_client.py**: GitHub APIとの通信をカプセル化
  - `create_comment()`: PR/Issueへのコメント作成メソッド
  - `get_pr_info()`: PR情報取得メソッド
  - エラーハンドリングとロギングを実装

#### フェーズ4: リポジトリ層の実装

**ステータス**: ✅ 完了

- [x] `app/repositories/session_repository.py` - セッション状態管理

**実装内容**:
- JSONファイルベースのセッション状態管理を実装
- `add_pending_session()`: 監視対象セッションの追加
- `get_pending_sessions()`: 監視中のセッション一覧取得
- `mark_session_completed()`: セッション完了マーク
- `mark_session_failed()`: セッション失敗マーク
- `get_session()`: 特定セッションの取得
- 将来的なRedis移行を考慮した設計

#### フェーズ5: サービス層の実装

**ステータス**: ✅ 完了

- [x] `app/services/webhook_service.py` - Webhook処理ロジック

**実装内容**:
- **webhook_service.py**: Webhookペイロードの処理ロジック
  - `process_webhook()`: メイン処理メソッド（非同期）
  - `_is_target_event()`: 対象イベントのフィルタリング
    - `action == "created"`の確認
    - 対象Botユーザー名の確認
    - コメントイベントの確認
  - `_extract_pr_info()`: PR情報の抽出
    - `issue_comment`と`pull_request_review_comment`の両方に対応
    - PR URL、コメント本文、PR番号、リポジトリ名を抽出
  - `_build_devin_prompt()`: Devin API用のプロンプト構築
    - PR URLとコメント内容を含む明確な指示を生成

#### フェーズ6: API層の実装

**ステータス**: ✅ 完了

- [x] `app/main.py` - FastAPI Webhookエンドポイント

**実装内容**:
- FastAPIアプリケーションの実装
- `POST /api/github/webhook`: GitHub Webhook受信エンドポイント
  - GitHub署名検証（セキュリティ）
  - ペイロードのパース
  - バックグラウンドタスクとして非同期処理
  - 即座に202 Acceptedを返してタイムアウト回避
- `GET /`: ルートエンドポイント（ヘルスチェック）
- `GET /health`: ヘルスチェックエンドポイント
- ロギング設定の実装

#### フェーズ7: 監視プロセスの実装

**ステータス**: ✅ 完了

- [x] `monitor.py` - Devinセッション監視スクリプト

**実装内容**:
- 独立したプロセスとして実行される監視スクリプト
- `SessionMonitor`クラスの実装
  - `check_sessions()`: 全監視中セッションの状態確認
  - `_check_session()`: 個別セッションの状態確認
    - `status_enum`に基づく分岐処理
    - `working`: 継続監視
    - `finished`: 完了処理
    - `blocked`: 失敗マーク
  - `_handle_finished_session()`: 完了セッションの処理
    - 新PR URLの抽出（structured_output、pull_requestフィールドから）
    - セッション完了マーク
    - 元PRへのコメント投稿
  - `_post_completion_comment()`: 完了通知コメントの投稿
- 設定可能なポーリング間隔（デフォルト30秒）
- エラーハンドリングとロギング

#### フェーズ8: エラーハンドリングとテストの実装

**ステータス**: ✅ 完了

- [x] `app/core/exceptions.py` - カスタム例外クラス
- [x] `app/core/logging_config.py` - ロギング設定の改善
- [x] ユニットテストスイートの作成

**実装内容**:
- **exceptions.py**: 階層的な例外クラス体系を実装
  - `RadeException`: 基底例外クラス
  - `ConfigurationError`: 設定エラー
  - `SecurityError`: セキュリティエラー
  - `DevinAPIError`: Devin APIエラー（HTTPステータスコードとレスポンスボディを含む）
  - `GitHubAPIError`: GitHub APIエラー（HTTPステータスコードとレスポンスボディを含む）
  - `RepositoryError`: リポジトリエラー
  - `WebhookProcessingError`: Webhook処理エラー
  - `SessionNotFoundError`: セッション未検出エラー
- **logging_config.py**: 構造化ロギング設定を実装
  - `setup_logging()`: アプリケーション全体のロギング設定
  - `get_logger()`: モジュール用ロガー取得関数
  - ファイル名と行番号を含む詳細なログフォーマット
  - サードパーティライブラリのログレベル調整
- **エラーハンドリングの強化**: 全レイヤーに適用
  - クライアント層: APIエラーを適切な例外に変換
  - リポジトリ層: データアクセスエラーを例外として処理
  - サービス層: ビジネスロジックエラーを適切に伝播
  - API層: バックグラウンドタスクでのエラーハンドリング強化
- **ユニットテスト**: pytestを使用した包括的なテストスイート
  - `test_exceptions.py`: 例外クラスのテスト
  - `test_security.py`: セキュリティモジュールのテスト
  - `test_devin_client.py`: DevinClientのテスト（モック使用）
  - `test_github_client.py`: GitHubClientのテスト（モック使用）
  - `test_session_repository.py`: SessionRepositoryのテスト
  - `test_webhook_service.py`: WebhookServiceのテスト（モック使用）
- **テスト設定**: `pyproject.toml`にpytest設定を追加
  - pytest、pytest-asyncio、pytest-cov、pytest-mockを依存関係に追加
  - カバレッジレポート設定
  - テストパスとファイルパターンの設定

## 技術スタック

- **Webフレームワーク**: FastAPI
- **HTTPクライアント**: httpx (非同期)
- **設定管理**: pydantic-settings
- **状態管理**: JSONファイル（初期実装）、将来的にRedis対応予定
- **パッケージマネージャー**: uv
- **テストフレームワーク**: pytest
- **Pythonバージョン**: >=3.13

## アーキテクチャ

### 責務分離（SoC）

プロジェクトは以下のレイヤーに明確に分離されています：

1. **API/エンドポイント層** (`app/main.py`)
   - HTTPリクエストの受付と応答のみ担当
   - 署名検証とペイロードパース

2. **サービス層** (`app/services/webhook_service.py`)
   - ビジネスロジックの中核
   - Webhookペイロードの解釈とDevinタスクのキックオフ

3. **クライアント層** (`app/clients/`)
   - 外部API（GitHub、Devin）との通信をカプセル化
   - HTTP通信の詳細を隠蔽

4. **リポジトリ層** (`app/repositories/session_repository.py`)
   - 状態（監視中セッション）の永続化を担当
   - データアクセスの詳細を隠蔽

5. **監視プロセス** (`monitor.py`)
   - 独立したポーリングロジック
   - セッション状態の監視と完了処理

## 使用方法

### 0. 依存関係のインストール

```bash
# uvを使用して依存関係をインストール
uv sync

# または、直接インストールする場合
uv pip install -e .
```

### 1. 環境変数の設定

`.env.example`を`.env`にコピーし、必要な値を設定：

```bash
cp .env.example .env
# .envファイルを編集
```

### 2. Webhookサーバーの起動

```bash
# 開発環境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# または
python -m app.main
```

### 3. 監視プロセスの起動

別のターミナルで：

```bash
python monitor.py
```

### 4. GitHub Webhookの設定

GitHubリポジトリの設定で、Webhook URLを設定：
- URL: `https://your-domain.com/api/github/webhook`
- Content type: `application/json`
- Secret: `.env`で設定した`GITHUB_WEBHOOK_SECRET`

## 注意事項

- ✅ 環境変数の設定が必要です（`.env.example`を参照）
- ✅ GitHub Webhookのシークレット設定が必要です
- ✅ Devin APIキーとGitHub Secret IDの登録が必要です
- ⚠️ GitHubトークンは任意ですが、PRへのコメント投稿には必要です
- ⚠️ 監視プロセスは独立して実行する必要があります（cronやsystemdで自動起動推奨）

## テストの実行方法

### テスト依存関係のインストール

```bash
# uvを使用してテスト依存関係をインストール
uv sync --extra test

# または、直接インストールする場合
uv pip install -e ".[test]"
```

### テストの実行

```bash
# 全テストの実行
pytest

# カバレッジレポート付きで実行
pytest --cov=app --cov-report=html

# 特定のテストファイルの実行
pytest tests/test_security.py

# 詳細出力で実行
pytest -v
```

### テストカバレッジ

テストカバレッジレポートは`htmlcov/index.html`に生成されます。

## 今後の改善予定

- [ ] 統合テストの追加（実際のAPIとの通信を含む）
- [ ] E2Eテストの追加
- [ ] Redisへの移行（スケーラビリティ向上）
- [ ] メトリクス収集（Prometheus等）
- [ ] エラーレポート機能（Sentry等）
- [ ] Docker化とデプロイ設定
- [ ] API仕様書の作成（OpenAPI/Swagger）
- [ ] CI/CDパイプラインの設定

## 変更履歴

### 2024年 - 初期実装

- ✅ 全コアコンポーネントの実装完了
- ✅ Webhookレシーバーの実装完了
- ✅ 監視プロセスの実装完了
- ✅ 開発ドキュメントの作成

### 2024年 - エラーハンドリングとテストの強化

- ✅ カスタム例外クラス体系の実装
- ✅ ロギング設定の改善（構造化ロギング）
- ✅ 全レイヤーへのエラーハンドリング強化
- ✅ 包括的なユニットテストスイートの作成
- ✅ pytest設定とテスト依存関係の追加
