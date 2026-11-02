"""
RapidOCR 引擎实现
- 速度快
- 行级检测框
- 默认引擎
- v37.7.14 cp44: 升级到 RapidOCR v3.9.2（PP-OCRv6 模型），包名从 rapidocr-onnxruntime 改为 rapidocr
- cp116: is_available() 捕获所有异常（不仅 ImportError）并存储真实错误，
  打破"打包后 OCR 不可用但看不到根因"的死循环。rapidocr 通过 __getattr__
  懒加载 main 模块，main.py 又触发 inference_engine.base 的类级
  OmegaConf.load(default_models.yaml)；任一环节失败（缺模块/缺数据文件/DLL
  加载失败）原本都被 except ImportError 静默吞掉，导致每次排查都在猜。
"""

import logging
import threading
import traceback
from typing import List, Optional

import numpy as np

from .base import BaseOCREngine, OCRResult
from privacyguard.utils.exceptions import OCRInspectionError

logger = logging.getLogger("privacyguard.rapidocr")


class RapidOCREngine(BaseOCREngine):
    """RapidOCR 引擎封装（v3.x）

    v40.1.4（性能）：引擎进程级共享（类级单例）——扫描 / 全文搜索 / 手动框选
    共用一份模型，避免每任务重复付 import+init+预热 ≈0.9s，也不再出现
    "主线程框选引擎 + worker 扫描引擎"双份模型驻留内存。推理以类级锁串行
    （onnxruntime session 本身线程安全，锁是 RapidOCR 管线整体状态的双保险）。
    """

    name = "rapidocr"
    supports_char_level = False

    # 类级共享状态（所有实例可见）
    _shared_engine = None
    _shared_lock = threading.Lock()
    _shared_init_failed = False
    _shared_last_error: Optional[str] = None

    def __init__(self):
        self._engine = None  # 保留属性名兼容（统一走类级共享）
        # cp57: 标记初始化是否已失败，避免每个图片块都重复尝试初始化导致性能退化
        self._init_failed = RapidOCREngine._shared_init_failed
        # cp116: 存储最近一次探测/初始化失败的真实异常，供上层拼入错误弹窗
        self._last_error: Optional[str] = RapidOCREngine._shared_last_error

    def get_last_error(self) -> Optional[str]:
        """cp116: 返回最近一次探测/初始化失败的真实错误文本（含 traceback）。"""
        return self._last_error

    def is_available(self) -> bool:
        """检查 RapidOCR 是否可用（v3.x 包名 rapidocr）。

        cp116: 捕获 Exception（不仅 ImportError）。rapidocr 的 __getattr__
        懒加载会触发整条导入链（main → ch_ppocr_* → inference_engine.base
        类级 OmegaConf.load），缺数据文件会抛 FileNotFoundError、DLL 加载
        失败会抛 OSError/RuntimeError，这些原本都不被 except ImportError 捕获。
        """
        try:
            from rapidocr import RapidOCR  # noqa: F401 — availability probe
            self._last_error = None
            return True
        except Exception as e:  # noqa: BLE001 — 探测语义：任何失败都视为不可用
            tb = traceback.format_exc()
            self._last_error = f"{type(e).__name__}: {e}\n{tb}"
            # 安全审计 v40.1: stderr 不打 {e}（可能含模型路径），只打类型名
            import sys
            print(f"[RapidOCR] is_available 探测失败: {type(e).__name__}", file=sys.stderr)
            return False

    def recognize(self, image: np.ndarray) -> List[OCRResult]:
        """
        使用 RapidOCR 识别图像

        Args:
            image: OpenCV 格式图像 (BGR)

        Returns:
            List[OCRResult]: 识别结果列表

        v37.7.14 cp44: 适配 RapidOCR v3.x 的 RapidOCROutput 返回结构。
        v1.x: `result, elapse = engine(img)`，`result = [[box, text, conf], ...]`
        v3.x: `output = engine(img)`，返回 RapidOCROutput 对象，需读取
              output.boxes (ndarray, shape (N,4,2))
              output.txts  (tuple of str)
              output.scores (tuple of float)
        v37.7.19 cp57: 初始化失败后设置 _init_failed 标志，避免重复尝试导致性能退化。
              模型文件缺失/损坏时，is_available() 仍返回 True（仅检查 import），
              若不设标志，每个图片块都会重新尝试 RapidOCR() 构造并失败。
        """
        # cp57: 初始化已失败，直接返回空列表，避免重复尝试
        cls = RapidOCREngine
        if cls._shared_init_failed:
            self._init_failed = True
            raise OCRInspectionError("OCR 模型初始化失败，请重新启动或检查安装包完整性")

        with cls._shared_lock:
            if self._engine is None and cls._shared_engine is None:
                # v37.7.14 cp44: RapidOCR v3.x 包名改为 rapidocr
                try:
                    from rapidocr import RapidOCR
                    from .model_paths import local_model_params
                    cls._shared_engine = RapidOCR(params=local_model_params())
                except Exception as e:
                    # cp57: 初始化失败（模型缺失/损坏等），标记并返回空列表
                    # 避免后续每个图片块都重复尝试 RapidOCR() 构造
                    # cp116: 存储真实错误（含 traceback），供上层拼入错误弹窗
                    tb = traceback.format_exc()
                    err = f"RapidOCR() 初始化失败: {type(e).__name__}: {e}\n{tb}"
                    cls._shared_last_error = err
                    self._last_error = err
                    # 安全审计 v40.1: 不打印 {e}/tb（可能含路径），只打类型名
                    print(f"[RapidOCR] 引擎初始化失败: {type(e).__name__}")
                    cls._shared_init_failed = True
                    self._init_failed = True
                    raise OCRInspectionError("OCR 模型初始化失败，请检查安装包完整性") from e
            if self._engine is None:
                # 实例属性作为共享单例的别名（兼容测试经 _engine 注入 mock 的既有接缝）
                self._engine = cls._shared_engine
            # v40.1.4：锁内推理——同一份引擎串行执行，跨线程（扫描 worker 与
            # 主线程框选）安全；顺序场景无锁竞争。
            output = self._engine(image)
        results = []

        # v37.7.14 cp44: v3.x 返回 RapidOCROutput 对象，需读取分离的 boxes/txts/scores
        # 兼容字段：v3.x 用 boxes/txts/scores；保留对 v1.x 的兼容（result 为 list[list]）
        boxes = None
        txts = None
        scores = None

        if hasattr(output, 'boxes') and hasattr(output, 'txts'):
            # v3.x: RapidOCROutput 对象
            boxes = output.boxes
            txts = output.txts
            scores = output.scores if hasattr(output, 'scores') else None
        elif isinstance(output, tuple) and len(output) >= 1 and output[0]:
            # v1.x 兼容: (result, elapse) 二元组
            # v37.7.18 cp50: 防御性修复 - v1.x 回退路径中 box 元素可能是 numpy 标量
            # 旧实现 list(p) 会产生 [np.float64, np.float64]，JSON 序列化报错
            # 改为 [float(p[0]), float(p[1])] 显式转换
            result = output[0]
            for line in result:
                box, text = line[0], line[1]
                try:
                    conf = float(line[2]) if len(line) > 2 and line[2] is not None else 0.9
                except (TypeError, ValueError):
                    conf = 0.9
                try:
                    box_list = [[float(p[0]), float(p[1])] for p in box] if hasattr(box, '__iter__') else box
                except (TypeError, ValueError, IndexError):
                    box_list = box
                results.append(OCRResult(
                    text=text,
                    box=box_list,
                    chars=[],
                    confidence=conf,
                    engine="rapidocr"
                ))
            return results

        if boxes is None or txts is None:
            # P2: output 既非 v3 RapidOCROutput 也非 v1 tuple —— 可能是 API 变更。
            # 静默返回空会让全 app OCR 零结果却看似"干净无命中"（漏脱风险）。
            # 仅在 output 非空时告警（空 output 是正常的空白页情形）。
            if output is not None:
                logger.warning("[RapidOCR] 无法识别的 OCR 输出结构，返回空结果: %s",
                               type(output).__name__)
            return results

        # v3.x 处理：boxes/txts/scores 三个平行序列
        # boxes 是 ndarray shape (N, 4, 2)，转换为 list of lists 以兼容下游代码
        n = len(txts)
        for i in range(n):
            text = txts[i]
            try:
                confidence = float(scores[i]) if scores is not None and i < len(scores) else 0.9
            except (TypeError, ValueError, IndexError):
                confidence = 0.9
            # 提取 box 并转换为 list[list[float]]
            try:
                raw_box = boxes[i]
                box_list = [[float(p[0]), float(p[1])] for p in raw_box]
            except (IndexError, TypeError):
                continue
            results.append(OCRResult(
                text=text,
                box=box_list,
                chars=[],
                confidence=confidence,
                engine="rapidocr"
            ))

        return results
