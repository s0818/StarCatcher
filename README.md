# Star Catcher

Unity 6 (6000.6.5f1) で作った簡単な2Dデモゲームです。

## 遊び方
- 落ちてくる **黄色い星** を拾うと +10点
- **赤い爆弾** に当たるとライフ -1（ライフは3）
- 時間がたつほど落下が速くなり、爆弾も増えます
- 操作：← → / A D キー、またはマウスを押したまま動かす
- スペースキーかクリックでスタート、Escで終了

## AIで作った素材とツール
- 3Dモデル（星・爆弾・プレイヤー）：[Meshy](https://www.meshy.ai) で生成（無料プラン、CC BY 4.0）
- 効果音・紹介動画のナレーション：[ElevenLabs](https://elevenlabs.io) で生成（無料プラン、非商用）
- BGM：プログラムで自動作曲（`Promo/tools/make_bgm.py`）
- 難易度：テスト用Botで1,000回の自動プレイを行い、その結果から調整（`Promo/data`）

コマンドラインオプション：`-theme 0〜3`（SPACE / OCEAN / SAKURA / NEON）、`-simulate N`（自動テスト）、`-record <フォルダ>`（録画）

## ビルド
Unityエディタのメニュー **StarCatcher > Build Windows** を選ぶか、コマンドラインで次を実行します：

```
Unity.exe -batchmode -quit -projectPath . -executeMethod BuildScript.BuildWindows
```

できたゲームは `Build/StarCatcher.exe` に出力されます。
