# 公开发布回执

`replay-publication.json` 由本地完整门禁成功后生成，锁定两篇公开研究载荷的原始字节SHA和已读回的月度私有原文记录数量。

```bash
node scripts/verify_replay_publish.mjs --write-public-receipt release/replay-publication.json
```

此模式实际读回本机私有原文并核SHA；原文、全文提取与私有审计不上传。

GitHub Actions仅验证公开载荷与本地回执完全一致，同时重新核月份×渠道配额、书目质量、公开隐私及dist范围：

```bash
node scripts/verify_replay_publish.mjs --public-receipt release/replay-publication.json
```

CI没有访问本机私有原件，不宣称独立重验PDF。回执是本地验收与公开发布之间的完整性绑定，不是第三方电子签名或原件公开副本。修改任一公开载荷会使旧回执失效，必须再次运行本地完整门禁；公开模式不能生成回执。

后续宏观复盘采用 `docs/macro-replay-template.md` 所规定的第二章模板。
