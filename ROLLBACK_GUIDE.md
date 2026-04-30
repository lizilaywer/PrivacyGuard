# 回滚指南（Word 批量替换迭代）

## 一键回滚

```bash
./restore_checkpoint.sh 20260302_word_batch_replace_cp0
```

可指定目标目录：

```bash
./restore_checkpoint.sh 20260302_word_batch_replace_cp0 /path/to/target
```

## 单文件回滚

1. 查看检查点目录：

```bash
ls -la backups/iteration_checkpoints/20260302_word_batch_replace_cp0
```

2. 先解压快照到临时目录：

```bash
mkdir -p /tmp/pg_restore_tmp

tar -xzf backups/iteration_checkpoints/20260302_word_batch_replace_cp0/snapshot_src.tar.gz -C /tmp/pg_restore_tmp
```

3. 拷回指定文件：

```bash
cp /tmp/pg_restore_tmp/main.py ./main.py
cp /tmp/pg_restore_tmp/config.json ./config.json
```

## 检查点说明

- cp0: 备份完成（实施前）
- cp1: UI 与规则弹窗
- cp2: 单文档应用与双栏预览
- cp3: 批量流程
- cp4: 测试通过待验收

## 注意事项

- 回滚会覆盖当前同名文件，请先自行备份当前工作区。
- 快照默认不包含 `dist/`、`releases/`、`venv*` 等大目录。
