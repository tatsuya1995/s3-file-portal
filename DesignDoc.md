# 📘 開発設計書: S3ファイル一覧・ダウンロード＋アップロード機能付きウェブサイト構成

---

## 1. 📌 概要

### 目的  
CloudFront経由でS3バケット内のファイルを一覧表示・ダウンロードできるWebページを提供し、さらに認証されたユーザーがPre-signed URLを使ってファイルをアップロードできる仕組みを構築する。

### 主な技術スタック
- AWS CDK (TypeScript)
- S3（静的ファイル格置・バージョン管理）
- CloudFront（公開用配信）
- Lambda@Edge（HTML一覧生成）
- Lambda（Pre-signed URL発行）
- IAM（セキュリティ制御）

---

## 2. 🗂️ 機能一覧

| 機能 | 説明 |
|--------|---------|
| 🔍 ファイル一覧表示 | バケット内のオブジェクト一覧取得→HTML生成 |
| 📅 ファイルダウンロード | 一覧内リンクから直接DL |
| 📄 ファイルアップロード | Pre-signed URLを取得しPUTリクエスト |
| ♻️ 同一ファイル名の上書き | S3バージョン管理ON |
| 🔐 セキュリティ制御 | CloudFront→IAM/サインURL等 |

---

## 3. 🏧 アーキテクチャ図

```
[Client]
   |
   v
[CloudFront]
   |
   +-- /           → Lambda@Edge　HTML生成
   +-- /upload-url → Lambda　Pre-signed URL
   |
   v
[S3 Bucket]　(versioned)
     ← (PUT via Pre-signed URL)
```

---

## 4. 🧱 AWSリソース詳細

### 4.1 S3バケット

| 項目 | 値 |
|------|----|
| 名称 | `FileHostingBucket` |
| バージョニング | 有効 (`versioned: true`) |
| 公開アクセス | 全ブロック |

---

### 4.2 CloudFront

- S3バケットをオリジンとする
- Lambda@Edgeを利用し、ルート `/` のリクエスト時にHTMLを返信

---

### 4.3 Lambda@Edge

| 項目 | 内容 |
|------|------|
| トリガー | CloudFront Origin Request |
| 処理内容 | S3一覧 → HTML生成 |
| 言語 | Python |

---

### 4.4 Lambda (Pre-signed URL)

| 項目 | 内容 |
|------|------|
| トリガー | API Gateway `/upload-url?filename=xxx` |
| 処理内容 | PUT用 Pre-signed URL を発行し返信 |
| 有効期限 | 約5分 |

---

## 5. 🖼️ HTMLページ仕様

- ファイル名 / サイズ / 更新日時 を表示
- ダウンロードリンク
- アップロードフォーム

### JavaScript

```js
async function uploadFile(file) {
  const res = await fetch(`/upload-url?filename=${encodeURIComponent(file.name)}`);
  const { url } = await res.json();

  const uploadRes = await fetch(url, {
    method: 'PUT',
    body: file,
  });

  if (uploadRes.ok) {
    alert("アップロード成功！");
    location.reload();
  } else {
    alert("アップロード失敗！");
  }
}
```

---

## 6. 🔐 セキュリティ設計

| 対象 | 制御内容 |
|------|----------|
| S3バケット | 全パブリックアクセスブロック |
| CloudFrontからのみ許可 | バケットポリシーで制限 |
| Pre-signed URLの発行制限 | IP/トークン/Cookieなどで認証 |

---

## 7. 🚀 CDKデプロイ

```bash
npx cdk deploy
```

パラメータ化 (cdk.json) をすれば、複数環境で再利用可能

---

## 8. 📄 ログ・監視

| 項目 | 手段 |
|------|------|
| Lambdaのログ | CloudWatch Logs |
| アップロード監視 | S3イベント（Lambdaなど） |
| CloudFrontログ | アクセスログ成形 |

---

## 9. 💪 テスト項目

| 内容 | 方法 |
|--------|------|
| 一覧表示 | CloudFront経由の表示を確認 |
| ダウンロードリンク | 実際にDLできるか |
| アップロード | フォームからのPUTを確認 |
| 上書きテスト | S3のバージョンを確認 |

---

## 10. ♻️ 拡張案

| 内容 | 概要 |
|--------|------|
| 認証連携 | Cognitoなどでログイン制御 |
| 管理画面 | 削除/履歴表示機能 |
| バージョン管理UI | 比較/ロールバック機能 |

---

## ✅ まとめ

- 開発はCDK+サーバレスの小覧で完結
- Pre-signed URLによりアップロードのセキュアな実現
- インフラエンジニアだけで実現可
- HTML/一覧生成も含め、形式化して利用可

