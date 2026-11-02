"""Word preview and scroll-sync methods extracted from MainWindow.

This module defines WordPreviewMixin, a pure method-container mixin.
MainWindow inherits from it to gain all Word preview rendering,
scroll synchronization, and interactive HTML injection methods.

All self.xxx references resolve to MainWindow attributes at runtime.
"""

import os
import re
import json
import logging

from bs4 import BeautifulSoup
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWebChannel import QWebChannel

logger = logging.getLogger("privacyguard.word_preview")

from privacyguard.utils.security import resource_path
from privacyguard.utils.helpers_word_preview import (
    HIGHLIGHT_FILTER_SOURCES,
    build_highlight_source_filter_script,
    build_word_panel_update_script,
    resolve_enabled_highlight_sources,
    resolve_word_ocr_replacements,
    should_reload_word_panel,
)
from privacyguard.utils.helpers_word_rules import (
    build_highlight_preview_segments,
    merge_word_matches_with_priority,
)

# Font stack constant (same as main.py module-level definition)
PREVIEW_FONT_STACK = (
    '"Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", '
    '"Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif'
)


def _load_js_asset(filename):
    """Load a JavaScript resource file from assets/js/."""
    _path = resource_path(os.path.join('assets', 'js', filename))
    with open(_path, 'r', encoding='utf-8') as _f:
        return _f.read()


_INTERACTIVE_JS_CODE = _load_js_asset('word_preview_interactive.js')

# 安全审计 v40.1.4（A1）：CSP——禁一切远程资源加载（img 仅 file:/data:，
# style 仅内联，script 仅内联 + qrc: 的 qwebchannel.js）。与 sanitize 剥外链、
# 导航白名单页构成三道防线，兜住"文档不出本机"的离线宣称。
_CSP_META = ('<meta http-equiv="Content-Security-Policy" '
             'content="default-src \'none\'; img-src file: data:; '
             'style-src \'unsafe-inline\'; script-src \'unsafe-inline\' qrc:">')


class WordPreviewMixin:
    """Mixin providing Word preview rendering and scroll-sync methods.

    Interface contract — MainWindow must provide these attributes/methods:

    Attributes (set in MainWindow.__init__ or setup_ui):
        word_data: dict — Word 文档文本块数据 {key: {text, ocr, manual}}
        word_preview: QWebEngineView — 原文预览面板
        word_preview_replaced: QWebEngineView — 替换后预览面板
        word_replace_rules: list — 替换规则列表
        manual_replace_prompt: bool — 手动替换弹窗开关
        replacement_text: str — 默认替换文本
        _preview_highlight_sources: set — 高亮来源过滤
        _word_scroll_sync_timer: QTimer — 滚动同步定时器
        _word_scroll_sync_generation: int — 同步代次（防过期回调）
        _word_scroll_sync_polling: bool — 是否正在轮询
        _word_preview_assets_base_url: QUrl — 预览资源基路径
        bridge: WebViewBridge | None — JS-Python 桥接对象

    Methods (defined in MainWindow):
        _is_word_web_view_valid(web_view) -> bool — WebView 可用性检查
        _set_info_bar_message(msg) — 状态栏消息
        _refresh_workbench_context() — 刷新工作台上下文
        _invalidate_word_scroll_sync() — 停用滚动同步
    """

    def render_word_preview(self):
        """渲染 Word 文档预览（HTML）"""
        if not self.word_doc:
            return

        try:
            source_changed = self._word_base_html is None or self._word_html_source_path != self.file_path

            # 仅在源文件变化或无缓存时进行 docx -> html 转换
            if source_changed:
                self._word_base_html = self._build_word_html_from_docx(self.file_path)
                self._word_html_source_path = self.file_path
                self._build_word_preview_documents()

            has_candidates = self._has_word_replacement_candidates()
            if not has_candidates:
                self.word_compare_user_hidden = False
            compare_enabled = has_candidates and not self.word_compare_user_hidden
            self.word_compare_mode = compare_enabled
            self._set_word_compare_mode(compare_enabled)
            self._refresh_word_compare_toggle()
            self.word_preview.show()

            # v37.6.1: 禁用 Word 预览的拖拽接受，让事件传递到 MainWindow
            # 解决 Word 打开后无法拖拽打开新文件的问题
            self.word_preview.setAcceptDrops(False)
            self.word_preview_replaced.setAcceptDrops(False)

            # 设置 WebChannel（仅首次）
            if not hasattr(self, 'bridge') or self.bridge is None:
                from main import WebViewBridge  # 延迟导入避免循环依赖
                channel = QWebChannel(self)
                self.bridge = WebViewBridge(self, self)
                channel.registerObject("pyBridge", self.bridge)
                self.word_web_channel = channel
            if self.word_web_channel is not None:
                self.word_preview.page().setWebChannel(self.word_web_channel)
                self.word_preview_replaced.page().setWebChannel(self.word_web_channel)

            self._pending_word_preview_blocks = self._build_word_original_panel_updates()
            base_url = self._word_preview_assets_base_url if self._word_preview_assets_base_url.isValid() else QUrl()
            if should_reload_word_panel(
                source_changed,
                self._word_preview_loaded_source_path,
                self.file_path,
                self._word_preview_ready
            ):
                self._word_preview_target_source_path = self.file_path
                self.word_preview.setHtml(self._word_preview_document_html or "", base_url)
            else:
                self._apply_word_panel_updates(self.word_preview, self._pending_word_preview_blocks)

            if compare_enabled:
                self._pending_word_replaced_blocks = self._build_word_replaced_panel_updates()
                self._word_replaced_html = self._word_replaced_document_html
                if should_reload_word_panel(
                    source_changed,
                    self._word_replaced_loaded_source_path,
                    self.file_path,
                    self._word_replaced_ready
                ):
                    self._word_replaced_target_source_path = self.file_path
                    self.word_preview_replaced.setHtml(self._word_replaced_document_html or "", base_url)
                else:
                    self._apply_word_panel_updates(self.word_preview_replaced, self._pending_word_replaced_blocks)
            else:
                self._word_replaced_html = None
                self._pending_word_replaced_blocks = None
                self._word_replaced_ready = False
                self._word_replaced_loaded_source_path = None
                self._word_replaced_target_source_path = None
                self.word_preview_replaced.setHtml("")

            self._configure_word_scroll_sync_panels()
            if compare_enabled:
                QTimer.singleShot(0, self._sync_word_compare_scroll_from_original)

            self._refresh_workbench_context()

        except Exception as e:
            # P2: 放宽为 Exception（与 extract_mixin 一致），避免 stray AttributeError/TypeError
            # 在 _word_preview_assets_base_url 首次初始化前传播崩溃；仅记类型名（可能含 PII）
            logger.error("[Word预览] 渲染预览失败: %s", type(e).__name__)
            QMessageBox.critical(self, "错误", f"渲染预览失败: {str(e)}")

    def _build_word_preview_documents(self):
        """构建只需首屏加载一次的 Word 预览文档。"""
        base_html = self._wrap_html_document(self._word_base_html or "")
        text_blocks = self._build_word_text_blocks()
        tagged_html = self._add_data_key_attributes(base_html, text_blocks)

        style = f"""
        <style>
            body {{ font-family: {PREVIEW_FONT_STACK}; padding: 20px; line-height: 1.6; }}
            p:empty {{ display: none; margin: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
            td, th {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
            mark.ocr-highlight {{ background-color: #ffeb3b; color: #000; display: inline; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
            mark.manual-highlight {{ background-color: #ff6b6b; color: #fff; display: inline; cursor: pointer; box-shadow: 0 0 0 1px #e03131; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
            mark.manual-highlight:hover {{ box-shadow: 0 0 0 1px #e03131, 0 0 4px rgba(225, 49, 49, 0.5); }}
            mark.replace-preview-highlight {{
                background-color: #ffd666;
                color: #2b1f00;
                border-radius: 3px;
                padding: 0 2px;
                box-decoration-break: clone;
                -webkit-box-decoration-break: clone;
                box-shadow: inset 0 -1px 0 rgba(43, 31, 0, 0.20);
            }}
            /* 按来源筛选：被筛掉的高亮去除背景/边框，仅保留文字，不影响内容 */
            mark[data-hl-filtered="1"] {{
                background-color: transparent !important;
                color: inherit !important;
                box-shadow: none !important;
                border: none !important;
                padding: 0 !important;
                cursor: auto !important;
            }}
        </style>
        """

        if "<head>" in tagged_html:
            tagged_html = tagged_html.replace("<head>", "<head>" + style, 1)
        else:
            tagged_html = style + tagged_html

        scroll_restore_script = self._get_word_preview_scroll_restore_script()
        document_html = self._inject_interactive_html(tagged_html, scroll_restore_script)

        self._word_tagged_html = tagged_html
        self._word_preview_document_html = document_html
        self._word_replaced_document_html = document_html
        self._word_preview_ready = False
        self._word_replaced_ready = False

    def _get_word_preview_scroll_restore_script(self):
        return '''<script>
    (function() {
        const STORAGE_KEY = 'word_preview_scroll_pos';
        let memoryScrollPos = 0;
        let syncTimeout = null;
        let syncFrame = null;
        let syncInterval = null;
        let lastNotifiedRatio = null;
        window.__wordPreviewPanelId = '';
        window.__wordScrollSyncEnabled = false;
        window.__wordScrollSyncApplying = false;

        function isLocalStorageAvailable() {
            try {
                const test = '__localStorage_test__';
                localStorage.setItem(test, test);
                localStorage.removeItem(test);
                return true;
            } catch (e) {
                return false;
            }
        }

        const useLocalStorage = isLocalStorageAvailable();

        function saveScroll() {
            const scrollY = window.pageYOffset || document.documentElement?.scrollTop || document.body?.scrollTop || 0;
            memoryScrollPos = scrollY;
            if (useLocalStorage) {
                try {
                    localStorage.setItem(STORAGE_KEY, scrollY.toString());
                } catch (e) {}
            }
        }

        function getMaxScrollY() {
            const docEl = document.documentElement;
            const body = document.body;
            const docHeight = Math.max(
                docEl ? docEl.scrollHeight : 0,
                body ? body.scrollHeight : 0
            );
            return Math.max(0, docHeight - window.innerHeight);
        }

        function getScrollRatio() {
            const scrollY = window.pageYOffset || document.documentElement?.scrollTop || document.body?.scrollTop || 0;
            const maxScrollY = getMaxScrollY();
            if (maxScrollY <= 0) {
                return 0;
            }
            return Math.max(0, Math.min(1, scrollY / maxScrollY));
        }

        function notifyScrollSync(force) {
            if (!window.__wordScrollSyncEnabled || window.__wordScrollSyncApplying) {
                return;
            }
            if (!pyBridge || !webChannelReady || typeof pyBridge.report_word_preview_scroll !== 'function') {
                return;
            }
            const ratio = getScrollRatio();
            if (!force && lastNotifiedRatio !== null && Math.abs(ratio - lastNotifiedRatio) < 0.002) {
                return;
            }
            lastNotifiedRatio = ratio;
            try {
                pyBridge.report_word_preview_scroll(window.__wordPreviewPanelId || '', ratio);
            } catch (e) {}
        }

        function refreshSyncInterval() {
            if (syncInterval) {
                clearInterval(syncInterval);
                syncInterval = null;
            }
            if (!window.__wordScrollSyncEnabled) {
                return;
            }
            syncInterval = setInterval(function() {
                notifyScrollSync(false);
            }, 80);
        }

        window.__setWordPreviewPanelId = function(panelId) {
            window.__wordPreviewPanelId = panelId || '';
        };

        window.__setWordPreviewScrollSyncEnabled = function(enabled) {
            window.__wordScrollSyncEnabled = !!enabled;
            refreshSyncInterval();
            if (window.__wordScrollSyncEnabled) {
                notifyScrollSync(true);
            }
        };

        window.__getWordPreviewScrollRatio = function() {
            return getScrollRatio();
        };

        window.__applyExternalWordScrollRatio = function(ratio) {
            const numericRatio = Number(ratio);
            if (!Number.isFinite(numericRatio)) {
                return;
            }
            const maxScrollY = getMaxScrollY();
            const targetRatio = Math.max(0, Math.min(1, numericRatio));
            const targetY = maxScrollY <= 0 ? 0 : Math.round(maxScrollY * targetRatio);
            lastNotifiedRatio = targetRatio;
            window.__wordScrollSyncApplying = true;
            window.scrollTo(0, targetY);
            setTimeout(function() {
                window.__wordScrollSyncApplying = false;
            }, 55);
        };

        function restoreScroll() {
            let savedPos = null;
            if (useLocalStorage) {
                try {
                    savedPos = localStorage.getItem(STORAGE_KEY);
                } catch (e) {}
            }
            if (!savedPos) {
                savedPos = memoryScrollPos.toString();
            }

            if (savedPos) {
                const targetY = parseInt(savedPos, 10);
                if (!isNaN(targetY) && targetY > 0) {
                    window.scrollTo(0, targetY);
                    setTimeout(function() {
                        window.scrollTo(0, targetY);
                    }, 10);
                }
            }
        }

        saveScroll();
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(saveScroll, 36);
            clearTimeout(syncTimeout);
            if (syncFrame !== null) {
                cancelAnimationFrame(syncFrame);
            }
            syncFrame = requestAnimationFrame(function() {
                syncFrame = null;
                notifyScrollSync(false);
            });
            syncTimeout = setTimeout(function() {
                notifyScrollSync(false);
            }, 24);
        });
        window.addEventListener('beforeunload', saveScroll);
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                saveScroll();
            } else if (window.__wordScrollSyncEnabled) {
                notifyScrollSync(true);
            }
        });
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', restoreScroll);
        }
        window.addEventListener('load', restoreScroll);
        requestAnimationFrame(restoreScroll);
        refreshSyncInterval();
    })();
    </script>'''

    def _build_word_text_blocks(self):
        text_blocks = {}
        for key, data in self.word_data.items():
            text = data.get("text", "")
            if text:
                # P2: 移除误导性的 "escaped" 字段（原值为未转义原文且从不被读取）
                text_blocks[key] = {"text": text}
        return text_blocks

    def _build_word_original_panel_updates(self):
        updates = {}
        for key, data in self.word_data.items():
            source_text = data.get("text", "")
            merged_matches = merge_word_matches_with_priority(
                source_text,
                [],
                self.replacement_text,
                manual_matches=data.get("manual", []),
                ocr_matches=data.get("ocr", [])
            )
            updates[key] = self._build_word_original_preview_fragment(key, source_text, merged_matches)
        return updates

    def _build_word_original_preview_fragment(self, key, source_text, merged_matches):
        from html import escape as html_escape

        segments = build_highlight_preview_segments(source_text, merged_matches)
        parts = []
        for segment in segments:
            value = segment.get("value", "")
            if value is None:
                value = ""
            if not isinstance(value, str):
                value = str(value)
            escaped_value = html_escape(value).replace("\n", "<br/>")

            if segment.get("type") != "highlight":
                parts.append(escaped_value)
                continue

            source = str(segment.get("source", "manual"))
            css_class = "manual-highlight" if source == "manual" else "ocr-highlight"
            attrs = [
                f'class="{css_class}"',
                f'data-source="{html_escape(source)}"',
                f'data-key="{html_escape(str(key))}"',
                f'data-start="{int(segment.get("start", 0))}"',
                f'data-end="{int(segment.get("end", 0))}"',
            ]
            title = "手动脱敏" if source == "manual" else str(segment.get("rule_name", "")).strip() or "智能脱敏"
            if title:
                attrs.append(f'title="{html_escape(title)}"')
            parts.append(f"<mark {' '.join(attrs)}>{escaped_value}</mark>")

        return "".join(parts)

    def _build_word_replaced_panel_updates(self):
        updates = {}
        for key, data in self.word_data.items():
            source_text = data.get("text", "")
            merged_matches = merge_word_matches_with_priority(
                source_text,
                self.word_replace_rules,
                self.replacement_text,
                manual_matches=data.get("manual", []),
                # cp63: 关键词行内替换（find|replace）优先于统一替换文本
                ocr_matches=resolve_word_ocr_replacements(
                    data.get("ocr", []),
                    getattr(self, "custom_keyword_rules", None),
                    self.replacement_text
                )
            )
            updates[key] = self._build_replaced_preview_fragment(source_text, merged_matches)
        return updates

    def _apply_word_panel_updates(self, web_view, block_updates):
        if web_view is None or not block_updates:
            return

        script = build_word_panel_update_script(block_updates)
        web_view.page().runJavaScript(script)
        # 增量更新后重新应用当前来源筛选（新插入的 <mark> 需同步筛选态）
        self._apply_highlight_source_filter(web_view)

    def _apply_highlight_source_filter(self, web_view=None):
        """将当前预览高亮来源筛选应用到指定面板（web_view=None 时应用于左右两个）。"""
        script = build_highlight_source_filter_script(self._preview_highlight_sources)
        targets = [web_view] if web_view is not None else [
            getattr(self, "word_preview", None),
            getattr(self, "word_preview_replaced", None),
        ]
        for view in targets:
            if self._is_word_web_view_valid(view):
                view.page().runJavaScript(script)

    def set_preview_highlight_sources(self, sources):
        """设置预览高亮可见来源并立即刷新两个面板。

        sources: rule/manual/ocr 的子集（任意可迭代）；None 表示全部显示。
        """
        self._preview_highlight_sources = resolve_enabled_highlight_sources(sources)
        self._apply_highlight_source_filter()

    def toggle_preview_highlight_source(self, source, enabled):
        """切换单个来源的可见性（供 UI 复选框回调）。"""
        if source not in HIGHLIGHT_FILTER_SOURCES:
            return
        current = set(self._preview_highlight_sources)
        if enabled:
            current.add(source)
        else:
            current.discard(source)
        self.set_preview_highlight_sources(current)

    def _configure_word_scroll_sync_panel(self, web_view, panel_id):
        """配置单个 Word 预览面板的滚动同步能力。"""
        if not self._is_word_web_view_valid(web_view):
            return
        sync_enabled = bool(
            self.word_doc
            and self.word_compare_mode
            and not self.word_compare_user_hidden
            and not web_view.isHidden()
        )
        panel_js = json.dumps(str(panel_id))
        enabled_js = "true" if sync_enabled else "false"
        web_view.page().runJavaScript(
            f"""
            if (window.__setWordPreviewPanelId) window.__setWordPreviewPanelId({panel_js});
            if (window.__setWordPreviewScrollSyncEnabled) window.__setWordPreviewScrollSyncEnabled({enabled_js});
            """
        )

    def _configure_word_scroll_sync_panels(self):
        """同步刷新左右 Word 预览面板的滚动联动状态。"""
        if hasattr(self, "word_preview"):
            self._configure_word_scroll_sync_panel(self.word_preview, "original")
        if hasattr(self, "word_preview_replaced"):
            self._configure_word_scroll_sync_panel(self.word_preview_replaced, "replaced")
        self._refresh_word_scroll_sync_timer()

    def _refresh_word_scroll_sync_timer(self):
        """按当前 Word 双栏状态启停滚动同步轮询。"""
        should_run = bool(
            self.word_doc
            and self.word_compare_mode
            and not self.word_compare_user_hidden
            and self._word_preview_ready
            and self._word_replaced_ready
            and self._is_word_web_view_valid(self.word_preview)
            and self._is_word_web_view_valid(self.word_preview_replaced)
            and not self.word_preview.isHidden()
            and not self.word_preview_replaced.isHidden()
        )
        if should_run:
            if not self._word_scroll_sync_timer.isActive():
                self._word_scroll_sync_timer.start()
        else:
            self._word_scroll_sync_timer.stop()
            self._word_scroll_sync_polling = False
            self._word_scroll_sync_pending_target = None
            self._word_scroll_sync_pending_ratio = None
            self._word_scroll_sync_last_ratios = {"original": None, "replaced": None}

    def _apply_word_scroll_ratio_to_panel(self, panel_id, ratio):
        """把滚动比例应用到指定 Word 预览面板。"""
        try:
            ratio_value = max(0.0, min(1.0, float(ratio)))
        except (TypeError, ValueError):
            return

        target_view = self.word_preview_replaced if panel_id == "replaced" else self.word_preview
        if not self._is_word_web_view_valid(target_view) or target_view.isHidden():
            return

        self._word_scroll_sync_pending_target = panel_id
        self._word_scroll_sync_pending_ratio = ratio_value
        target_view.page().runJavaScript(
            f"if (window.__applyExternalWordScrollRatio) window.__applyExternalWordScrollRatio({ratio_value:.6f});"
        )

    def _sync_word_compare_scroll(self, source_panel, ratio):
        """双栏对比模式下，同步左右预览滚动位置。"""
        if not self.word_compare_mode or self.word_compare_user_hidden:
            return
        if source_panel not in {"original", "replaced"}:
            return
        try:
            ratio_value = max(0.0, min(1.0, float(ratio)))
        except (TypeError, ValueError):
            return
        if (
            self._word_scroll_sync_pending_target == source_panel
            and self._word_scroll_sync_pending_ratio is not None
            and abs(ratio_value - float(self._word_scroll_sync_pending_ratio)) <= 0.02
        ):
            self._word_scroll_sync_pending_target = None
            self._word_scroll_sync_pending_ratio = None
            return
        if source_panel == "original":
            self._apply_word_scroll_ratio_to_panel("replaced", ratio_value)
        else:
            self._apply_word_scroll_ratio_to_panel("original", ratio_value)

    def _sync_word_compare_scroll_from_original(self):
        """用左侧原文预览的当前位置对齐右侧替换预览。"""
        if not self.word_compare_mode or self.word_compare_user_hidden:
            return
        if not self._word_preview_ready or not self._word_replaced_ready:
            return
        if not self._is_word_web_view_valid(self.word_preview):
            return
        if not self._is_word_web_view_valid(self.word_preview_replaced):
            return
        if self.word_preview.isHidden() or self.word_preview_replaced.isHidden():
            return

        generation = self._word_scroll_sync_generation
        self.word_preview.page().runJavaScript(
            "window.__getWordPreviewScrollRatio ? window.__getWordPreviewScrollRatio() : 0;",
            lambda ratio, sync_generation=generation: self._sync_word_compare_scroll_from_original_callback(ratio, sync_generation),
        )

    def _sync_word_compare_scroll_from_original_callback(self, ratio, generation):
        """仅在同步代次仍有效时，把左侧滚动位置应用到右侧。"""
        if generation != self._word_scroll_sync_generation:
            return
        self._apply_word_scroll_ratio_to_panel("replaced", ratio)

    def _poll_word_compare_scroll_sync(self):
        """轮询双栏 Word 预览滚动位置，作为联动兜底方案。"""
        if self._word_scroll_sync_polling:
            return
        if not self._word_scroll_sync_timer.isActive():
            return
        if not self.word_compare_mode or self.word_compare_user_hidden:
            return
        if not self._word_preview_ready or not self._word_replaced_ready:
            return
        if not self._is_word_web_view_valid(self.word_preview):
            return
        if not self._is_word_web_view_valid(self.word_preview_replaced):
            return
        if self.word_preview.isHidden() or self.word_preview_replaced.isHidden():
            return

        self._word_scroll_sync_polling = True
        generation = self._word_scroll_sync_generation
        self.word_preview.page().runJavaScript(
            "window.__getWordPreviewScrollRatio ? window.__getWordPreviewScrollRatio() : 0;",
            lambda ratio, sync_generation=generation: self._handle_word_scroll_sync_original_ratio(ratio, sync_generation),
        )

    def _handle_word_scroll_sync_original_ratio(self, original_ratio, generation):
        """获取左侧比例后继续读取右侧比例。"""
        if generation != self._word_scroll_sync_generation:
            self._word_scroll_sync_polling = False
            return
        try:
            normalized_original = max(0.0, min(1.0, float(original_ratio or 0.0)))
        except (TypeError, ValueError):
            normalized_original = 0.0

        if not self._is_word_web_view_valid(self.word_preview_replaced) or self.word_preview_replaced.isHidden():
            self._word_scroll_sync_polling = False
            return

        self.word_preview_replaced.page().runJavaScript(
            "window.__getWordPreviewScrollRatio ? window.__getWordPreviewScrollRatio() : 0;",
            lambda replaced_ratio, sync_generation=generation: self._handle_word_scroll_sync_ratio_pair(normalized_original, replaced_ratio, sync_generation),
        )

    def _handle_word_scroll_sync_ratio_pair(self, original_ratio, replaced_ratio, generation):
        """比较双栏滚动位置，并同步变化更明显的一侧。"""
        if generation != self._word_scroll_sync_generation:
            self._word_scroll_sync_polling = False
            return
        try:
            normalized_original = max(0.0, min(1.0, float(original_ratio or 0.0)))
        except (TypeError, ValueError):
            normalized_original = 0.0
        try:
            normalized_replaced = max(0.0, min(1.0, float(replaced_ratio or 0.0)))
        except (TypeError, ValueError):
            normalized_replaced = 0.0

        previous_original = self._word_scroll_sync_last_ratios.get("original")
        previous_replaced = self._word_scroll_sync_last_ratios.get("replaced")
        self._word_scroll_sync_last_ratios = {
            "original": normalized_original,
            "replaced": normalized_replaced,
        }

        if previous_original is None or previous_replaced is None:
            self._word_scroll_sync_polling = False
            return

        delta_original = abs(normalized_original - previous_original)
        delta_replaced = abs(normalized_replaced - previous_replaced)
        threshold = 0.012

        if (
            self._word_scroll_sync_pending_target == "replaced"
            and abs(normalized_replaced - float(self._word_scroll_sync_pending_ratio or 0.0)) <= 0.02
        ):
            delta_replaced = 0.0
            self._word_scroll_sync_pending_target = None
            self._word_scroll_sync_pending_ratio = None
        elif (
            self._word_scroll_sync_pending_target == "original"
            and abs(normalized_original - float(self._word_scroll_sync_pending_ratio or 0.0)) <= 0.02
        ):
            delta_original = 0.0
            self._word_scroll_sync_pending_target = None
            self._word_scroll_sync_pending_ratio = None

        if delta_original >= threshold and delta_original > delta_replaced:
            self._apply_word_scroll_ratio_to_panel("replaced", normalized_original)
        elif delta_replaced >= threshold and delta_replaced > delta_original:
            self._apply_word_scroll_ratio_to_panel("original", normalized_replaced)

        self._word_scroll_sync_polling = False

    def _on_word_preview_load_finished(self, ok):
        self._word_preview_ready = bool(ok)
        self._word_preview_loaded_source_path = self._word_preview_target_source_path if ok else None
        if ok and self._pending_word_preview_blocks:
            self._apply_word_panel_updates(self.word_preview, self._pending_word_preview_blocks)
        if ok:
            self._apply_highlight_source_filter(self.word_preview)
            self._configure_word_scroll_sync_panel(self.word_preview, "original")
            self._refresh_word_scroll_sync_timer()
            QTimer.singleShot(0, self._sync_word_compare_scroll_from_original)

    def _on_word_replaced_load_finished(self, ok):
        self._word_replaced_ready = bool(ok)
        self._word_replaced_loaded_source_path = self._word_replaced_target_source_path if ok else None
        if ok and self._pending_word_replaced_blocks:
            self._apply_word_panel_updates(self.word_preview_replaced, self._pending_word_replaced_blocks)
        if ok:
            self._apply_highlight_source_filter(self.word_preview_replaced)
            self._configure_word_scroll_sync_panel(self.word_preview_replaced, "replaced")
            self._refresh_word_scroll_sync_timer()
            QTimer.singleShot(0, self._sync_word_compare_scroll_from_original)

    def _add_data_key_attributes(self, html, text_blocks):
        """使用 BeautifulSoup 为文本块添加 data-key 属性

        Args:
            html: HTML 字符串
            text_blocks: 文本块字典 {key: {'text': 原始文本, 'escaped': 转义文本}}

        Returns:
            修改后的 HTML 字符串
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 支持的标签列表（扩展）
            target_tags = ['p', 'td', 'th', 'li', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a']

            # v40.1.4（F1 性能）：单次遍历建索引，替代"每块×每标签×全树重扫"的
            # 三重循环（复杂度 O(块数×13×全树) → O(全树)；实测 600 块 901ms → 数十 ms）。
            # 语义与原实现严格一致：按 target_tags 优先级、同标签内文档序，
            # 取第一个归一化文本完全匹配且未被占用的元素（pop 保证一次性占用）。
            _index = {}
            for element in soup.find_all(target_tags):
                if element.get('data-key'):
                    continue  # 跳过已经有 data-key 的元素（与原实现一致）
                normalized = ' '.join(element.get_text().split())
                if not normalized:
                    continue
                _index.setdefault((element.name, normalized), []).append(element)

            for key, info in text_blocks.items():
                original_text = info['text']
                if not original_text or not original_text.strip():
                    continue

                # 归一化文本：将多个空白字符合并为单个空格
                normalized_original = ' '.join(original_text.split())

                for tag_name in target_tags:
                    candidates = _index.get((tag_name, normalized_original))
                    if candidates:
                        element = candidates.pop(0)
                        element['data-key'] = key
                        element['data-original-text'] = original_text
                        element['data-word-block'] = '1'
                        break

            return str(soup)

        except (ImportError, AttributeError, TypeError, ValueError) as e:
            import logging as _lg
            _lg.getLogger(__name__).warning("[Word预览] BeautifulSoup 后备: %s", type(e).__name__)
            return self._add_data_key_regex_fallback(html, text_blocks)

    def _add_data_key_regex_fallback(self, html, text_blocks):
        """使用正则表达式为文本块添加 data-key 属性（后备方案）

        Args:
            html: HTML 字符串
            text_blocks: 文本块字典

        Returns:
            修改后的 HTML 字符串
        """
        from html import escape as html_escape

        for key, info in text_blocks.items():
            original_text = info['text']
            escaped_text = html_escape(original_text)
            # P2: key 一并转义（与 _add_data_key_attributes 主路径对称），防注入隐患
            escaped_key = html_escape(str(key))

            # 尝试各种 HTML 标签
            patterns = [
                (
                    f'<p([^>]*)>({re.escape(escaped_text)})</p>',
                    f'<p\\1 data-key="{escaped_key}" data-original-text="{escaped_text}" data-word-block="1">\\2</p>'
                ),
                (
                    f'<td([^>]*)>({re.escape(escaped_text)})</td>',
                    f'<td\\1 data-key="{escaped_key}" data-original-text="{escaped_text}" data-word-block="1">\\2</td>'
                ),
                (
                    f'<li([^>]*)>({re.escape(escaped_text)})</li>',
                    f'<li\\1 data-key="{escaped_key}" data-original-text="{escaped_text}" data-word-block="1">\\2</li>'
                ),
                (
                    f'<span([^>]*)>({re.escape(escaped_text)})</span>',
                    f'<span\\1 data-key="{escaped_key}" data-original-text="{escaped_text}" data-word-block="1">\\2</span>'
                ),
                (
                    f'<div([^>]*)>({re.escape(escaped_text)})</div>',
                    f'<div\\1 data-key="{escaped_key}" data-original-text="{escaped_text}" data-word-block="1">\\2</div>'
                ),
            ]

            for pattern, replacement in patterns:
                if f'data-key="{escaped_key}"' not in html:
                    if re.search(pattern, html):
                        html = re.sub(pattern, replacement, html, count=1)
                        break

        return html

    def _inject_interactive_html(self, html, scroll_restore=''):
        """注入 JavaScript 交互逻辑用于右键菜单和脱敏操作

        v36.4: 重构为使用模块级常量 _INTERACTIVE_JS_CODE，简化函数逻辑

        Args:
            html: 要注入的 HTML
            scroll_restore: 滚动恢复脚本（可选）
        """
        # 包装 HTML 为完整文档（如果不是的话）
        html = self._wrap_html_document(html)

        # 注入脚本
        qwebchannel_js = '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>'

        if '</head>' in html:
            html = html.replace('</head>', qwebchannel_js + _INTERACTIVE_JS_CODE + scroll_restore + '</head>')
        else:
            html = qwebchannel_js + _INTERACTIVE_JS_CODE + scroll_restore + html

        return html

    # 安全审计 v40.1.4（A1）：CSP——禁一切远程资源加载（img 仅 file:/data:，
    # style 仅内联，script 仅内联 + qrc: 的 qwebchannel.js）。与 sanitize 剥外链、
    # 导航白名单页构成三道防线，兜住"文档不出本机"的离线宣称。
    # 注意：模块级常量（非类属性），单元测试的 SimpleNamespace 桩可直接调用本方法。

    def _wrap_html_document(self, html):
        """将 HTML 包装成完整文档（如果不是完整文档的话）

        Args:
            html: 输入的 HTML 字符串

        Returns:
            完整的 HTML 文档字符串（保证含 CSP meta）
        """
        is_full_document = '<html' in html.lower() or '<!doctype' in html.lower()

        if is_full_document:
            # 已是完整文档：若无 CSP 则注入到 </head>（或 <head>）之后
            low = html.lower()
            if 'http-equiv="content-security-policy"' not in low:
                if '</head>' in low:
                    html = re.sub(r'</head>', _CSP_META + '</head>', html,
                                  count=1, flags=re.IGNORECASE)
                elif '<head>' in low:
                    html = re.sub(r'<head\s*>', '<head>' + _CSP_META, html,
                                  count=1, flags=re.IGNORECASE)
            return html

        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{_CSP_META}
<style>
    body {{ margin: 0; padding: 20px; font-family: {PREVIEW_FONT_STACK}; line-height: 1.6; }}
    img {{ max-width: 100%; height: auto; }}
    p {{ margin: 0 0 10px 0; }}
</style>
</head>
<body>
{html}
</body>
</html>'''



