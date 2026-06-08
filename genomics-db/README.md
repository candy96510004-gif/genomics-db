# GWAS Methods DB

個人 GWAS 分析方法知識庫，追蹤 PRS、LDSC、Fine-mapping、MR 等方法的最新發展。

## 分類

| 分類 | 說明 |
|------|------|
| PRS | 多基因風險分數 |
| LDSC | 遺傳力 / 遺傳相關性估計 |
| Fine-mapping | 因果變異定位 |
| MR | 孟德爾隨機化 |
| GWAS QC | 關聯分析與品質控制 |

## 使用方式

### 瀏覽網頁
開啟 `docs/index.html` 或訪問 GitHub Pages 網址。

### Python 腳本管理資料

```bash
cd scripts

# 新增方法
python add_method.py add

# 對某方法新增論文（支援 PubMed 自動查詢）
python add_method.py paper

# 列出所有方法
python add_method.py list

# 搜尋
python add_method.py search SuSiE

# 匯出 JSON 到 docs/data/
python add_method.py export
```

### 更新到 GitHub Pages

```bash
git add .
git commit -m "update: 新增 XXX 方法"
git push
```

推送後約 1-2 分鐘，GitHub Pages 會自動更新。

## 檔案結構

```
genomics-db/
├── docs/
│   ├── index.html          # 網頁介面
│   └── data/
│       └── methods.json    # 所有資料
├── scripts/
│   └── add_method.py       # 管理腳本
└── README.md
```
