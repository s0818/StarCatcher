# Star Catcher

Unity 6 (6000.6.5f1) で作った簡単な2Dデモゲームです。

## 遊び方
- 落ちてくる **黄色い星** を拾うと +10点
- **赤い爆弾** に当たるとライフ -1（ライフは3）
- 時間がたつほど落下が速くなり、爆弾も増えます
- 操作：← → / A D キー、またはマウスを押したまま動かす
- スペースキーかクリックでスタート、Escで終了

## ビルド
Unityエディタのメニュー **StarCatcher > Build Windows** を選ぶか、コマンドラインで次を実行します：

```
Unity.exe -batchmode -quit -projectPath . -executeMethod BuildScript.BuildWindows
```

できたゲームは `Build/StarCatcher.exe` に出力されます。
