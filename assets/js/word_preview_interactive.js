<script>
    let pyBridge = null;
    let webChannelReady = false;

    document.addEventListener('DOMContentLoaded', function() {
        // 初始化 QWebChannel
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            try {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    pyBridge = channel.objects.pyBridge;
                    if (pyBridge) {
                        webChannelReady = true;
                    }
                });
            } catch (e) {
                console.error('QWebChannel error:', e);
            }
        }
        setupContextMenu();
    });

    // v35.1: 备用右键位置（用于复杂 DOM 结构中 getSelection() 返回空值的情况）
    let lastContextMenuEvent = null;

    function setupContextMenu() {
        // v35.1: 使用捕获阶段监听（更可靠，在事件冒泡前捕获）
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            lastContextMenuEvent = {
                clientX: e.clientX,
                clientY: e.clientY,
                target: e.target
            };
            handleContextMenu(e);
        }, true);  // true = 捕获阶段

        // v35.1: mousedown 事件预先保存右键位置（备用方案）
        document.addEventListener('mousedown', function(e) {
            if (e.button === 2) {  // 右键
                lastContextMenuEvent = {
                    clientX: e.clientX,
                    clientY: e.clientY,
                    target: e.target
                };
            }
        }, true);

        document.addEventListener('click', function(e) {
            if (!e.target.closest('#redaction-menu')) {
                hideContextMenu();
            }
        });
    }

    // v35.1: 增强的右键菜单处理函数
    function handleContextMenu(e) {
        const target = e.target;
        let selection = window.getSelection();
        let selectedText = selection.toString().trim();

        // 查找点击的目标是否是手动脱敏标记或其内部元素
        let highlightElement = target.closest('.manual-highlight');

        // 点击手动脱敏标记
        if (highlightElement) {
            console.log('[ContextMenu] 点击了手动脱敏标记');
            showRemoveMenu(e.clientX, e.clientY, highlightElement);
            return;
        }

        // 选择了文本（主要路径）
        if (selectedText.length > 0) {
            // v36.5: 移除敏感信息日志，仅记录操作类型
            console.log('[ContextMenu] 选择了文本（已隐藏内容）');
            try {
                const range = selection.getRangeAt(0);
                showAddMenu(e.clientX, e.clientY, selection, selectedText);
            } catch (err) {
                console.warn('[ContextMenu] getRangeAt 失败，尝试备用方案:', err);
                // 备用方案：使用预先保存的位置
                if (lastContextMenuEvent) {
                    tryFallbackTextDetection(e, target);
                }
            }
            return;
        }

        // v35.1: 备用方案 - 尝试从点击位置获取文本
        console.log('[ContextMenu] getSelection() 为空，尝试备用检测');
        tryFallbackTextDetection(e, target);
    }

    // v35.1: 备用文本检测（当 window.getSelection() 失败时）
    function tryFallbackTextDetection(e, target) {
        // 方案1: 检查目标元素是否包含文本
        let textElement = target;

        // 向上查找包含 data-key 的文本块
        for (let i = 0; i < 10 && textElement; i++) {
            if (textElement.dataset && textElement.dataset.key) {
                console.log('[tryFallbackTextDetection] 找到 data-key 元素:', textElement.dataset.key);
                // 显示一个提示菜单（v36.1 安全修复：使用配置对象）
                const menu = createMenu([
                    { text: '请在文本上拖动选择后再右键', disabled: true }
                ]);
                positionMenu(menu, e.clientX, e.clientY);
                setTimeout(hideContextMenu, 2000);
                return;
            }
            textElement = textElement.parentNode;
        }

        // 未找到 data-key，显示提示
        console.warn('[tryFallbackTextDetection] 未找到有效的文本块');
    }

    function showRemoveMenu(x, y, element) {
        const key = element.dataset.key;
        const start = parseInt(element.dataset.start);
        const end = parseInt(element.dataset.end);

        console.log('[showRemoveMenu] key:', key, 'start:', start, 'end:', end);

        // v36.1 安全修复：使用配置对象替代 HTML 字符串
        const menu = createMenu([
            { text: '❌ 撤销脱敏', action: 'remove', key: key, start: start, end: end }
        ]);
        positionMenu(menu, x, y);
        attachMenuHandlers();
    }

    function showAddMenu(x, y, selection, selectedText) {
        const range = selection.getRangeAt(0);
        const textInfo = findTextPosition(selectedText, range);

        // 即使 textInfo 为 null 也不直接返回，使用全局模式
        let buttonConfigs = [];

        if (!textInfo || textInfo.mode === 'global' || textInfo.key === '__GLOBAL__') {
            // 降级到全局模式：只显示全文脱敏选项
            console.log('[showAddMenu] 使用全局降级模式');
            // v36.1 安全修复：使用配置对象替代 HTML 字符串
            buttonConfigs = [
                { text: '📄 全文脱敏此内容', action: 'add-global-only', textData: selectedText }
            ];
        } else {
            // 正常情况：提供精确和全局两种选项
            buttonConfigs = [
                { text: '🎯 选中区域添加脱敏', action: 'add-exact', key: textInfo.key, start: textInfo.start, end: textInfo.end, textData: selectedText },
                { text: '📄 整篇相同字节添加脱敏', action: 'add-global', key: textInfo.key, textData: selectedText }
            ];
        }

        const menu = createMenu(buttonConfigs);
        positionMenu(menu, x, y);
        attachMenuHandlers();
    }

    function attachMenuHandlers() {
        const menu = document.getElementById('redaction-menu');
        if (!menu) return;

        menu.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const action = this.dataset.action;
                const key = this.dataset.key;
                const start = parseInt(this.dataset.start);
                const end = parseInt(this.dataset.end);
                const text = this.dataset.text;

                if (action === 'remove') {
                    callRemove(key, start, end);
                } else if (action === 'add-exact') {
                    callAddExact(key, start, end, text);
                } else if (action === 'add-global') {
                    callAddGlobal(key, text);
                } else if (action === 'add-global-only') {
                    // 全局降级模式，不需要 key 参数
                    callAddGlobal(null, text);
                }
            });
        });
    }

    function callRemove(key, start, end) {
        console.log('[callRemove] 调用撤销: key=' + key + ' start=' + start + ' end=' + end);
        console.log('[callRemove] pyBridge=', pyBridge, 'webChannelReady=', webChannelReady);
        if (pyBridge && webChannelReady) {
            try {
                pyBridge.remove_manual_redaction(key, start, end);
                console.log('[callRemove] ✓ 撤销调用成功');
            } catch(e) {
                console.error('[callRemove] ✗ 撤销调用失败:', e);
            }
        } else {
            console.error('[callRemove] ✗ pyBridge 或 webChannel 未就绪');
        }
        hideContextMenu();
    }

    function callAddExact(key, start, end, text) {
        if (pyBridge && webChannelReady) {
            pyBridge.add_manual_redaction(key, start, end, text);
        }
        hideContextMenu();
        const selection = window.getSelection();
        selection.removeAllRanges();
    }

    function callAddGlobal(key, text) {
        // v36.5: 移除敏感信息日志
        console.log('[callAddGlobal] 调用全局脱敏（文本已隐藏）');
        if (pyBridge && webChannelReady) {
            // key 为 null 时表示纯全局模式
            pyBridge.add_manual_redaction_global(key || '', text);
        }
        hideContextMenu();
        const selection = window.getSelection();
        selection.removeAllRanges();
    }

    function findTextPosition(selectedText, range) {
        try {
            // v36.5: 移除敏感信息日志
            console.log('[findTextPosition] ========== 开始查找 ==========');
            console.log('[findTextPosition] 选中文本（已隐藏内容）');
            console.log('[findTextPosition] Range:', {
                startContainer: range.startContainer?.nodeName,
                startOffset: range.startOffset,
                endContainer: range.endContainer?.nodeName,
                endOffset: range.endOffset
                // 移除 text 字段，避免泄露敏感信息
            });

            let container = range.commonAncestorContainer;
            if (!container) {
                console.warn('[findTextPosition] ✗ 无 commonAncestorContainer，使用全局降级');
                return createGlobalFallbackResult(selectedText);
            }

            console.log('[findTextPosition] commonAncestorContainer:', container.nodeName, container.nodeType);

            // 如果是文本节点，获取其父元素
            if (container.nodeType === 3) {
                container = container.parentNode;
            }

            // 查找包含 data-key 的元素（向上遍历）
            let element = container;
            let maxIterations = 50;
            let iterations = 0;
            let foundKey = null;

            while (element && iterations < maxIterations) {
                iterations++;
                if (element.dataset && element.dataset.key) {
                    foundKey = element.dataset.key;
                    console.log('[findTextPosition] ✓ 找到 data-key:', foundKey);
                    break;
                }
                element = element.parentNode;
                if (element === document.body || element === document.documentElement) {
                    console.warn('[findTextPosition] 到达文档顶部，未找到 data-key，尝试文本内容定位');
                    break;  // 不返回 null，继续尝试其他方法
                }
            }

            // 方法 1: 精确计算（如果有 data-key）
            if (foundKey && element) {
                const key = foundKey;

                // === 方法 1a: 直接使用 Range 计算位置（最可靠）===
                try {
                    const textNodes = [];
                    const walker = document.createTreeWalker(
                        element,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: function(node) {
                                // 接受所有非空文本节点
                                return NodeFilter.FILTER_ACCEPT;
                            }
                        }
                    );

                    let node;
                    while (node = walker.nextNode()) {
                        textNodes.push(node);
                    }

                    console.log('[findTextPosition] 找到', textNodes.length, '个文本节点');

                    // 打印所有文本节点信息
                    for (let i = 0; i < Math.min(textNodes.length, 10); i++) {
                        const tn = textNodes[i];
                        console.log(`[findTextPosition] 节点[${i}]:`, {
                            text: tn.textContent.substring(0, 30),
                            isStart: tn === range.startContainer,
                            isEnd: tn === range.endContainer
                        });
                    }

                    // 计算起始位置
                    let startOffset = 0;
                    let startFound = false;

                    // 特殊处理：如果 startContainer 是元素节点，找到它的第一个文本节点
                    let startContainer = range.startContainer;
                    if (startContainer.nodeType === 1) {  // 元素节点
                        console.log('[findTextPosition] startContainer 是元素节点，查找第一个文本子节点');
                        for (let i = 0; i < textNodes.length; i++) {
                            if (element.contains(textNodes[i]) || element === textNodes[i].parentNode) {
                                startContainer = textNodes[i];
                                break;
                            }
                        }
                    }

                    for (let i = 0; i < textNodes.length; i++) {
                        const tn = textNodes[i];
                        if (!startFound) {
                            if (tn === startContainer || (startContainer && tn.contains && tn.contains(startContainer))) {
                                startOffset += range.startOffset;
                                startFound = true;
                                console.log('[findTextPosition] ✓ 起始节点匹配, offset:', range.startOffset);
                            } else {
                                startOffset += tn.textContent.length;
                            }
                        }
                    }

                    // 计算结束位置
                    let endOffset = 0;
                    let endFound = false;

                    let endContainer = range.endContainer;
                    if (endContainer.nodeType === 1) {
                        console.log('[findTextPosition] endContainer 是元素节点，查找第一个文本子节点');
                        for (let i = 0; i < textNodes.length; i++) {
                            if (element.contains(textNodes[i]) || element === textNodes[i].parentNode) {
                                endContainer = textNodes[i];
                                break;
                            }
                        }
                    }

                    for (let i = 0; i < textNodes.length; i++) {
                        const tn = textNodes[i];
                        if (!endFound) {
                            if (tn === endContainer || (endContainer && tn.contains && tn.contains(endContainer))) {
                                endOffset += range.endOffset;
                                endFound = true;
                                console.log('[findTextPosition] ✓ 结束节点匹配, offset:', range.endOffset);
                            } else {
                                endOffset += tn.textContent.length;
                            }
                        }
                    }

                    console.log('[findTextPosition] Range 计算结果:', { startFound, endFound, startOffset, endOffset });

                    if (startFound && endFound && startOffset >= 0 && endOffset > startOffset) {
                        console.log('[findTextPosition] ✓✓✓ Range 计算成功 ✓✓✓');
                        return { key, start: startOffset, end: endOffset };
                    }
                } catch (e) {
                    console.error('[findTextPosition] Range 计算出错:', e);
                }

                // === 方法 1b: 文本匹配（后备）===
                console.log('[findTextPosition] 尝试文本匹配方法...');
                let originalText = '';
                if (element.dataset.originalText) {
                    // 安全解码：使用 DOMParser 替代 innerHTML，防止 XSS
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(element.dataset.originalText, 'text/html');
                    originalText = doc.body.textContent || '';
                    console.log('[findTextPosition] 原始文本长度:', originalText.length);
                }

                if (!originalText) {
                    originalText = element.textContent || '';
                }

                // 尝试直接匹配
                let foundStart = originalText.indexOf(selectedText);
                if (foundStart !== -1) {
                    console.log('[findTextPosition] ✓✓✓ 直接匹配成功 ✓✓✓');
                    return { key, start: foundStart, end: foundStart + selectedText.length };
                }

                // 尝试归一化匹配
                const normalizedSelected = selectedText.replace(/\s+/g, ' ').trim();
                const normalizedOriginal = originalText.replace(/\s+/g, ' ');
                foundStart = normalizedOriginal.indexOf(normalizedSelected);
                if (foundStart !== -1) {
                    console.log('[findTextPosition] ✓✓✓ 归一化匹配成功 ✓✓✓');
                    return { key, start: foundStart, end: foundStart + selectedText.length };
                }
            }

            // 方法 2: 文本内容定位（遍历所有 data-key 元素）
            console.log('[findTextPosition] 尝试文本内容定位方法...');
            const textResult = findPositionByTextContent(selectedText);
            if (textResult) {
                console.log('[findTextPosition] ✓✓✓ 文本内容定位成功 ✓✓✓');
                return textResult;
            }

            // 方法 3: 全局脱敏降级
            console.log('[findTextPosition] 所有精确方法失败，使用全局降级模式');
            return createGlobalFallbackResult(selectedText);

        } catch (e) {
            console.error('[findTextPosition] 异常:', e);
            return createGlobalFallbackResult(selectedText);
        }
    }

    function createGlobalFallbackResult(selectedText) {
        console.log('[findTextPosition] 创建全局降级结果，文本长度:', selectedText.length);
        return {
            key: '__GLOBAL__',
            start: 0,
            end: selectedText.length,
            mode: 'global',
            text: selectedText
        };
    }

    function findPositionByTextContent(selectedText) {
        // 遍历所有带有 data-key 的元素，查找包含选中文本的元素
        const elements = document.querySelectorAll('[data-key]');
        const normalizedSelected = selectedText.replace(/\s+/g, ' ').trim();

        for (const el of elements) {
            const key = el.dataset.key;
            if (!key || key === '__GLOBAL__') continue;

            let originalText = '';
            if (el.dataset.originalText) {
                // 安全解码：使用 DOMParser 替代 innerHTML，防止 XSS
                const parser = new DOMParser();
                const doc = parser.parseFromString(el.dataset.originalText, 'text/html');
                originalText = doc.body.textContent || '';
            } else {
                originalText = el.textContent || '';
            }

            const normalizedOriginal = originalText.replace(/\s+/g, ' ');
            const foundStart = normalizedOriginal.indexOf(normalizedSelected);

            if (foundStart !== -1) {
                console.log('[findTextPosition] 文本内容定位找到匹配，key:', key);
                return { key, start: foundStart, end: foundStart + selectedText.length };
            }
        }

        return null;
    }

    // v36.1 安全修复：使用 DOM 方法替代 innerHTML，防止 XSS
    function createMenu(buttonConfigs) {
        hideContextMenu();
        const menu = document.createElement('div');
        menu.id = 'redaction-menu';
        menu.style.cssText = 'position:fixed; background:white; border:1px solid #ddd; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); padding:8px 0; z-index:10000; min-width:150px;';

        const buttonStyle = 'display:block; width:100%; padding:8px 16px; border:none; background:none; text-align:left; cursor:pointer; font-size:14px; color:#333;';

        // 安全创建按钮元素，避免使用 innerHTML
        buttonConfigs.forEach(config => {
            const btn = document.createElement('button');
            btn.style.cssText = buttonStyle;
            btn.onmouseover = () => btn.style.backgroundColor = '#f5f5f5';
            btn.onmouseout = () => btn.style.backgroundColor = 'transparent';

            // 设置按钮文本（自动转义 HTML）
            btn.textContent = config.text || '';

            // 设置 data 属性
            if (config.action) btn.setAttribute('data-action', config.action);
            if (config.key !== undefined) btn.setAttribute('data-key', config.key);
            if (config.start !== undefined) btn.setAttribute('data-start', config.start);
            if (config.end !== undefined) btn.setAttribute('data-end', config.end);
            if (config.textData !== undefined) btn.setAttribute('data-text', config.textData);

            // 设置 disabled 状态
            if (config.disabled) {
                btn.disabled = true;
                btn.style.color = '#999';
                btn.style.cursor = 'default';
            }

            menu.appendChild(btn);
        });

        document.body.appendChild(menu);
        return menu;
    }

    function positionMenu(menu, x, y) {
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function hideContextMenu() {
        const menu = document.getElementById('redaction-menu');
        if (menu) menu.remove();
    }
</script>
