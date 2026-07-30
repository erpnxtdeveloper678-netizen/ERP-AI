class ERPAI {
    constructor() {
        if (window.__erpAiInstance) {
            console.warn(
                "ERP AI: an instance is already running on this page — skipping " +
                "duplicate initialization. If you keep seeing this, check for " +
                "erp_ai.js being registered/loaded from more than one place " +
                "(hooks.py, a Client Script, or a stale cached bundle)."
            );
            return window.__erpAiInstance;
        }
        window.__erpAiInstance = this;

        document.querySelectorAll("#erp-ai-window, #erp-ai-button").forEach(el => el.remove());

        this.messages = [];
        this.conversation = null;
        this.typing = false;
        this.dragging = false;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;
        this.attachedFileContent = null;
        this.attachedFileName = "";

        this.resizing = false;
        this.resizeStartX = 0;
        this.resizeStartY = 0;
        this.resizeStartWidth = 0;
        this.resizeStartHeight = 0;
        this.minWidth = 320;
        this.minHeight = 420;

        this.injectStyles();
        this.createButton();
        this.createWindow();
    }

    injectStyles() {
        if (document.getElementById("erp-ai-styles")) return;

        const style = document.createElement("style");
        style.id = "erp-ai-styles";
        style.textContent = `
            :root {
                --erp-ink: #0F172A;
                --erp-slate: #475569;
                --erp-slate-soft: #94A3B8;
                --erp-border: #E2E8F0;
                --erp-surface: #FFFFFF;
                --erp-surface-soft: #F8FAFC;
                --erp-accent: #2563EB;
                --erp-accent-dark: #1D4ED8;
                --erp-accent-soft: #EFF6FF;
                --erp-signature: #F59E0B;
                --erp-online: #22C55E;
                --erp-ease: cubic-bezier(0.22, 1, 0.36, 1);
            }

            #erp-ai-button {
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.28), 0 2px 6px rgba(15, 23, 42, 0.12);
                transition: transform 220ms var(--erp-ease), box-shadow 220ms var(--erp-ease);
            }
            #erp-ai-button:hover {
                transform: translateY(-2px) scale(1.04);
                box-shadow: 0 12px 28px rgba(37, 99, 235, 0.36), 0 3px 8px rgba(15, 23, 42, 0.14);
            }
            #erp-ai-button:active { transform: translateY(0) scale(0.98); }

            #erp-ai-window {
                border-radius: 18px;
                box-shadow: 0 20px 48px rgba(15, 23, 42, 0.18), 0 4px 16px rgba(15, 23, 42, 0.08);
                border: 1px solid var(--erp-border);
                animation: erp-ai-window-in 260ms var(--erp-ease);
            }
            @keyframes erp-ai-window-in {
                from { opacity: 0; transform: translateY(10px) scale(0.98); }
                to   { opacity: 1; transform: translateY(0) scale(1); }
            }

            #erp-ai-resize-handle:hover { opacity: 1 !important; }

            .erp-ai-row {
                animation: erp-ai-msg-in 320ms var(--erp-ease) both;
            }
            @keyframes erp-ai-msg-in {
                from { opacity: 0; transform: translateY(6px); }
                to   { opacity: 1; transform: translateY(0); }
            }

            .erp-ai-message {
                transition: box-shadow 160ms var(--erp-ease);
            }

            .erp-ai-avatar.erp-ai-thinking {
                position: relative;
            }
            .erp-ai-avatar.erp-ai-thinking::after {
                content: "";
                position: absolute;
                inset: -4px;
                border-radius: 50%;
                border: 2px solid var(--erp-signature);
                opacity: 0.55;
                animation: erp-ai-glow-pulse 1.4s var(--erp-ease) infinite;
            }
            @keyframes erp-ai-glow-pulse {
                0%   { transform: scale(0.85); opacity: 0.55; }
                70%  { transform: scale(1.25); opacity: 0; }
                100% { transform: scale(1.25); opacity: 0; }
            }

            .erp-ai-loading-dots {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 2px 0;
            }
            .erp-ai-loading-dots span {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background: var(--erp-accent);
                display: inline-block;
                animation: erp-ai-dot-beat 1.1s ease-in-out infinite;
            }
            .erp-ai-loading-dots span:nth-child(1) { animation-delay: 0ms; }
            .erp-ai-loading-dots span:nth-child(2) { animation-delay: 140ms; }
            .erp-ai-loading-dots span:nth-child(3) { animation-delay: 280ms; }
            @keyframes erp-ai-dot-beat {
                0%, 60%, 100% { transform: translateY(0) scale(1); opacity: 0.5; }
                30% { transform: translateY(-4px) scale(1.15); opacity: 1; }
            }

            .erp-ai-message table tbody tr {
                animation: erp-ai-row-in 260ms var(--erp-ease) both;
            }
            @keyframes erp-ai-row-in {
                from { opacity: 0; transform: translateY(4px); }
                to   { opacity: 1; transform: translateY(0); }
            }
            .erp-ai-message table {
                font-variant-numeric: tabular-nums;
            }
            .erp-ai-message td, .erp-ai-message th {
                font-variant-numeric: tabular-nums;
            }

            .export-csv-btn {
                transition: background 160ms var(--erp-ease), transform 120ms var(--erp-ease), border-color 160ms var(--erp-ease);
            }
            .export-csv-btn:hover { background: var(--erp-accent-soft) !important; border-color: var(--erp-accent) !important; }
            .export-csv-btn:active { transform: scale(0.98); }

            #erp-ai-input:focus {
                outline: none;
                box-shadow: 0 0 0 3px var(--erp-accent-soft);
                border-color: var(--erp-accent) !important;
            }

            #erp-ai-send {
                transition: transform 140ms var(--erp-ease), box-shadow 140ms var(--erp-ease);
            }
            #erp-ai-send:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }
            #erp-ai-send:active { transform: translateY(0) scale(0.94); }

            .erp-ai-avatar {
                border-radius: 50%;
                background: var(--erp-accent-soft);
                width: 28px;
                height: 28px;
                flex-shrink: 0;
            }
            .erp-ai-message.assistant {
                background: var(--erp-surface-soft);
                border: 1px solid var(--erp-border);
                border-radius: 14px 14px 14px 4px;
                color: var(--erp-ink);
            }
            .erp-ai-message.user {
                background: var(--erp-ink);
                border-radius: 14px 14px 4px 14px;
                color: #fff;
            }

            @media (prefers-reduced-motion: reduce) {
                #erp-ai-window, .erp-ai-row, .erp-ai-message table tbody tr,
                .erp-ai-avatar.erp-ai-thinking::after, .erp-ai-loading-dots span {
                    animation: none !important;
                    transition: none !important;
                }
            }
        `;
        document.head.appendChild(style);
    }

    async loadTemplate() {
        const response = await fetch("/assets/erp_ai/chat.html");
        if (!response.ok) throw new Error("Failed to load ERP AI template.");
        return await response.text();
    }

    createButton() {
        if (document.getElementById("erp-ai-button")) return;
        const button = document.createElement("div");
        button.id = "erp-ai-button";
        button.innerHTML = `
            <div class="button-logo-inside" style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; font-weight: bold; font-family: inherit;">
                <span style="color: #2563eb; font-size: 15px;">E</span><span style="color: #0f172a; font-size: 15px;">AI</span>
            </div>
        `;
        document.body.appendChild(button);
        button.addEventListener("click", () => this.toggleWindow());
    }

    async createWindow() {
        if (document.getElementById("erp-ai-window")) return;
        const windowElement = document.createElement("div");
        windowElement.id = "erp-ai-window";
        windowElement.style.display = "none";
        document.body.appendChild(windowElement);

        try {
            const html = await this.loadTemplate();
            if (document.querySelectorAll("#erp-ai-window").length > 1) {
                windowElement.remove();
                return;
            }
            windowElement.innerHTML = html;
            this.setupResizableWindow();
            this.bindEvents();
        } catch (e) {
            console.error(e);
            windowElement.innerHTML = `<div style="padding:20px; color:red; font-weight:bold;">Failed to load ERP AI UI.</div>`;
        }
    }

    setupResizableWindow() {
        const windowEl = document.getElementById("erp-ai-window");
        if (!windowEl) return;

        const computedStyle = window.getComputedStyle(windowEl);
        const computedPosition = computedStyle.position;
        if (computedPosition !== "fixed" && computedPosition !== "absolute") {
            windowEl.style.position = "fixed";
        }
        if (!windowEl.style.zIndex) {
            windowEl.style.zIndex = "9999";
        }

        const hasExplicitOffset = [computedStyle.top, computedStyle.left, computedStyle.right, computedStyle.bottom]
            .some(v => v && v !== "auto");
        if (!hasExplicitOffset) {
            windowEl.style.right = "24px";
            windowEl.style.bottom = "90px";
        }

        windowEl.style.minWidth = this.minWidth + "px";
        windowEl.style.minHeight = this.minHeight + "px";
        windowEl.style.maxWidth = "95vw";
        windowEl.style.maxHeight = "90vh";
        windowEl.style.boxSizing = "border-box";

        if (!document.getElementById("erp-ai-resize-handle")) {
            const handle = document.createElement("div");
            handle.id = "erp-ai-resize-handle";
            handle.title = "Drag to resize";
            handle.style.cssText = `
                position: absolute;
                right: 0px;
                bottom: 0px;
                width: 22px;
                height: 22px;
                cursor: nwse-resize;
                z-index: 100;
                background:
                    linear-gradient(135deg, transparent 0 50%, #94a3b8 50% 60%, transparent 60% 100%),
                    linear-gradient(135deg, transparent 0 70%, #94a3b8 70% 80%, transparent 80% 100%);
                opacity: 0.85;
                border-bottom-right-radius: 18px;
            `;
            windowEl.appendChild(handle);

            handle.addEventListener("mousedown", (e) => {
                e.preventDefault();
                e.stopPropagation();

                this.resizing = true;
                const r = windowEl.getBoundingClientRect();
                this.resizeStartX = e.clientX;
                this.resizeStartY = e.clientY;
                this.resizeStartWidth = r.width;
                this.resizeStartHeight = r.height;
                document.body.style.userSelect = "none";
            });
        }

        document.addEventListener("mousemove", (e) => {
            if (!this.resizing) return;

            const deltaX = e.clientX - this.resizeStartX;
            const deltaY = e.clientY - this.resizeStartY;

            let newWidth = this.resizeStartWidth + deltaX;
            let newHeight = this.resizeStartHeight + deltaY;

            const maxWidth = window.innerWidth * 0.95;
            const maxHeight = window.innerHeight * 0.90;

            newWidth = Math.min(Math.max(newWidth, this.minWidth), maxWidth);
            newHeight = Math.min(Math.max(newHeight, this.minHeight), maxHeight);

            windowEl.style.width = newWidth + "px";
            windowEl.style.height = newHeight + "px";
        });

        document.addEventListener("mouseup", () => {
            if (this.resizing) {
                this.resizing = false;
                document.body.style.userSelect = "";
            }
        });

        window.addEventListener("resize", () => {
            const r = windowEl.getBoundingClientRect();
            const maxWidth = window.innerWidth * 0.95;
            const maxHeight = window.innerHeight * 0.90;

            if (r.width > maxWidth) windowEl.style.width = maxWidth + "px";
            if (r.height > maxHeight) windowEl.style.height = maxHeight + "px";

            const newRect = windowEl.getBoundingClientRect();
            if (newRect.right > window.innerWidth) {
                windowEl.style.left = Math.max(0, window.innerWidth - newRect.width) + "px";
            }
            if (newRect.bottom > window.innerHeight) {
                windowEl.style.top = Math.max(0, window.innerHeight - newRect.height) + "px";
            }
        });
    }

    bindEvents() {
        const input = document.getElementById("erp-ai-input");
        document.getElementById("erp-ai-close").addEventListener("click", () => this.hideWindow());
        document.getElementById("erp-ai-minimize").addEventListener("click", () => this.hideWindow());
        document.getElementById("erp-ai-send").addEventListener("click", () => this.sendMessage());

        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        input.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = this.scrollHeight + "px";
        });

        const fileInput = document.getElementById("erp-ai-file-input");
        const attachBtn = document.getElementById("erp-ai-attach-btn");

        if (attachBtn && fileInput) {
            fileInput.addEventListener("change", (e) => {
                const file = e.target.files[0];
                if (!file) return;

                this.attachedFileName = file.name;
                const reader = new FileReader();

                reader.onload = (event) => {
                    this.attachedFileContent = event.target.result;
                    let previewEl = document.getElementById("erp-ai-file-preview");
                    if (previewEl) {
                        previewEl.style.display = "inline-block";
                        previewEl.innerText = `📎 ${this.attachedFileName}`;
                    }
                };

                reader.readAsText(file);
            });
        }

        document.querySelectorAll(".erp-ai-suggestion").forEach(button => {
            button.addEventListener("click", () => {
                input.value = button.dataset.message;
                input.dispatchEvent(new Event("input"));
                input.focus();
            });
        });

        const toggleSidebarBtn = document.getElementById("erp-ai-toggle-sidebar");
        const sidebar = document.getElementById("erp-ai-sidebar");
        if (toggleSidebarBtn && sidebar) {
            toggleSidebarBtn.addEventListener("click", () => {
                const isOpen = sidebar.classList.toggle("open");
                toggleSidebarBtn.classList.toggle("active", isOpen);
                if (isOpen) this.loadConversationsList();
            });
        }

        const newChatBtn = document.getElementById("erp-ai-new-chat");
        if (newChatBtn) {
            newChatBtn.addEventListener("click", () => this.startNewChat());
        }

        const conversationsList = document.getElementById("erp-ai-conversations-list");
        if (conversationsList) {
            conversationsList.addEventListener("click", (e) => {
                const item = e.target.closest(".erp-ai-conv-item");
                if (item && item.dataset.name) {
                    this.loadConversationHistory(item.dataset.name);
                }
            });
        }

        this.enableDragging();
    }

    startNewChat() {
        this.conversation = null;
        this.messages = [];
        const container = document.getElementById("erp-ai-messages");
        if (container) container.innerHTML = "";
        const welcome = document.getElementById("erp-ai-welcome");
        if (welcome) welcome.style.display = "";
        document.querySelectorAll(".erp-ai-conv-item.active").forEach(el => el.classList.remove("active"));
        this.focusInput();
    }

    loadConversationsList() {
        const listEl = document.getElementById("erp-ai-conversations-list");
        if (!listEl) return;

        frappe.call({
            method: "erp_ai.api.get_user_conversations",
            callback: (r) => {
                const data = (r.message && r.message.status === "success") ? r.message.data : [];

                if (!data || data.length === 0) {
                    listEl.innerHTML = '<div class="erp-ai-sidebar-empty">No conversations yet</div>';
                    return;
                }

                listEl.innerHTML = "";
                data.forEach(c => {
                    const item = document.createElement("div");
                    item.className = "erp-ai-conv-item" + (c.name === this.conversation ? " active" : "");
                    item.dataset.name = c.name;
                    item.title = c.title || c.name;
                    item.textContent = c.title || c.name;
                    listEl.appendChild(item);
                });
            },
            error: () => {
                listEl.innerHTML = '<div class="erp-ai-sidebar-empty">Could not load conversations</div>';
            }
        });
    }

    loadConversationHistory(conversationName) {
        frappe.call({
            method: "erp_ai.api.load_conversation",
            args: { conversation_name: conversationName },
            callback: (r) => {
                if (!r.message || r.message.status !== "success") {
                    console.error("ERP AI: failed to load conversation", r.message);
                    return;
                }

                this.conversation = r.message.name;
                this.messages = Array.isArray(r.message.messages) ? r.message.messages : [];

                const container = document.getElementById("erp-ai-messages");
                if (container) container.innerHTML = "";
                const welcome = document.getElementById("erp-ai-welcome");
                if (welcome) welcome.style.display = "none";

                this.messages.forEach(m => {
                    this.addMessage(m.content, m.role === "user" ? "user" : "assistant");
                });

                document.querySelectorAll(".erp-ai-conv-item").forEach(el => {
                    el.classList.toggle("active", el.dataset.name === conversationName);
                });

                this.scrollToBottom();
            }
        });
    }

    enableDragging() {
        const windowEl = document.getElementById("erp-ai-window");
        const header = document.getElementById("erp-ai-header");

        if (!windowEl || !header) {
            console.warn(
                "ERP AI: dragging not enabled — could not find #erp-ai-window and/or " +
                "#erp-ai-header in the DOM. Make sure the header bar element in " +
                "chat.html has id=\"erp-ai-header\"."
            );
            return;
        }

        header.addEventListener("dragstart", (e) => e.preventDefault());

        header.addEventListener("mousedown", (e) => {
            if (e.target.tagName === "BUTTON" || e.target.closest("button")) return;

            this.dragging = true;
            const rect = windowEl.getBoundingClientRect();

            windowEl.style.left = rect.left + "px";
            windowEl.style.top = rect.top + "px";
            windowEl.style.right = "auto";
            windowEl.style.bottom = "auto";

            this.dragOffsetX = e.clientX - rect.left;
            this.dragOffsetY = e.clientY - rect.top;
            document.body.style.userSelect = "none";
        });

        document.addEventListener("mousemove", (e) => {
            if (!this.dragging) return;
            windowEl.style.left = (e.clientX - this.dragOffsetX) + "px";
            windowEl.style.top = (e.clientY - this.dragOffsetY) + "px";
        });

        document.addEventListener("mouseup", () => {
            if (this.dragging) {
                this.dragging = false;
                document.body.style.userSelect = "";
            }
        });
    }

    showWindow() {
        document.getElementById("erp-ai-window").style.display = "flex";
        this.focusInput();
    }

    hideWindow() {
        document.getElementById("erp-ai-window").style.display = "none";
    }

    toggleWindow() {
        const win = document.getElementById("erp-ai-window");
        win.style.display === "flex" ? this.hideWindow() : this.showWindow();
    }

    focusInput() {
        const input = document.getElementById("erp-ai-input");
        if (input) input.focus();
    }

    async sendMessage() {
        const input = document.getElementById("erp-ai-input");
        const message = input.value.trim();

        if (!message && !this.attachedFileContent) return;

        input.value = "";
        input.style.height = "auto";

        const welcome = document.getElementById("erp-ai-welcome");
        if (welcome) welcome.style.display = "none";

        let displayMessage = message;
        if (this.attachedFileName) {
            displayMessage += `\n[مرفق: ${this.attachedFileName}]`;
        }

        this.messages.push({ role: "user", content: message });
        this.addMessage(displayMessage, "user");

        let argsPayload = {
            message: message,
            conversation: JSON.stringify(this.messages.slice(0, -1)),
            conversation_name: this.conversation
        };

        if (this.attachedFileContent) {
            argsPayload.file_data = this.attachedFileContent;
            argsPayload.file_name = this.attachedFileName;
        }

        this.attachedFileContent = null;
        this.attachedFileName = "";
        const previewEl = document.getElementById("erp-ai-file-preview");
        if (previewEl) previewEl.style.display = "none";
        const fileInput = document.getElementById("erp-ai-file-input");
        if (fileInput) fileInput.value = "";

        this.showTyping();

        try {
            const response = await frappe.call({
                method: "erp_ai.api.ask",
                args: argsPayload
            });

            this.hideTyping();

            if (response && response.message && response.message.reply) {
                if (response.message.conversation_name) {
                    const isNewConversation = this.conversation !== response.message.conversation_name;
                    this.conversation = response.message.conversation_name;
                    const sidebar = document.getElementById("erp-ai-sidebar");
                    if (isNewConversation && sidebar && sidebar.classList.contains("open")) {
                        this.loadConversationsList();
                    }
                }

                let fullReply = response.message.reply;

                if (Array.isArray(fullReply)) {
                    fullReply = fullReply.join("");
                }

                this.addMessage(fullReply, "assistant");
                this.messages.push({ role: "assistant", content: fullReply });
            } else {
                this.addMessage("No response received from AI.", "assistant");
            }

        } catch (e) {
            console.error(e);
            this.hideTyping();
            this.addMessage("Something went wrong.", "assistant");
        }
    }

    extractTableData(mdText) {
        try {
            let lines = mdText.split('\n').filter(line => line.trim().includes('|'));
            let separatorIndex = lines.findIndex(line => line.match(/\|[-\s:]+\|/));

            if (separatorIndex < 1) return null;

            let parseRow = (row) => {
                let trimmed = row.trim();
                if (trimmed.startsWith('|')) trimmed = trimmed.substring(1);
                if (trimmed.endsWith('|')) trimmed = trimmed.substring(0, trimmed.length - 1);
                return trimmed.split('|').map(c => c.trim());
            };

            let headers = parseRow(lines[separatorIndex - 1]);
            let data = [];

            for (let i = separatorIndex + 1; i < lines.length; i++) {
                if (!lines[i].trim().includes('|')) break;
                let cells = parseRow(lines[i]);
                let rowObj = {};
                headers.forEach((h, idx) => {
                    rowObj[h] = cells[idx] !== undefined ? cells[idx] : "";
                });
                data.push(rowObj);
            }
            return data.length > 0 ? data : null;
        } catch (e) {
            console.error("Error parsing table:", e);
            return null;
        }
    }

    escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value === undefined || value === null ? "" : String(value);
        return div.innerHTML;
    }

    addMessage(text, sender) {
        const container = document.getElementById("erp-ai-messages");
        const row = document.createElement("div");
        row.className = "erp-ai-row " + sender;

        const avatar = document.createElement("div");
        avatar.className = "erp-ai-avatar";
        avatar.innerHTML = sender === "user" ? "👤" : '<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';

        const bubble = document.createElement("div");
        bubble.className = "erp-ai-message " + sender;

        let cleanText = typeof text === "object" ? (text.reply || JSON.stringify(text)) : text;
        cleanText = String(cleanText).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g, "").trim();

        if (sender === "assistant") {
            const tableData = this.extractTableData(String(cleanText));

            if (tableData && tableData.length > 0) {
                let textParts = String(cleanText).split(/\|.*\|/);
                let textWithoutTable = textParts[0] ? textParts[0].trim() : "";

                let htmlOutput = `<div class="ai-text-part" style="margin-bottom: 10px;">${
                    window.frappe && frappe.markdown
                        ? frappe.markdown(textWithoutTable)
                        : this.escapeHtml(textWithoutTable)
                }</div>`;

                htmlOutput += `<div class="table-responsive" style="margin-top: 8px; margin-bottom: 8px; overflow-x: auto;">
                    <table class="table table-bordered table-striped" style="width: 100%; background: #fff; font-size: 11px; color: #333; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f1f3f5;">`;

                let headers = Object.keys(tableData[0]);
                headers.forEach(h => {
                    htmlOutput += `<th style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(h)}</th>`;
                });

                htmlOutput += `</tr></thead><tbody>`;

                tableData.forEach((row, rowIndex) => {
                    htmlOutput += `<tr style="animation-delay: ${Math.min(rowIndex * 55, 500)}ms;">`;
                    headers.forEach(h => {
                        htmlOutput += `<td style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(row[h] || '')}</td>`;
                    });
                    htmlOutput += `</tr>`;
                });

                htmlOutput += `</tbody></table></div>`;

                let encodedData = encodeURIComponent(JSON.stringify(tableData));
                htmlOutput += `
                    <div class="message-actions" style="margin-top: 10px; clear: both; width: 100%;">
                        <button type="button" class="btn btn-xs btn-default export-csv-btn" data-csv-payload="${encodedData}" style="cursor: pointer; background: #f8f9fa; border: 1px solid #cbd5d1; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: #2c3e50; width: 100%; box-sizing: border-box;">
                            <i class="fa fa-download"></i> Download (CSV)
                        </button>
                    </div>
                `;

                bubble.innerHTML = htmlOutput;

                const exportBtn = bubble.querySelector(".export-csv-btn");
                if (exportBtn) {
                    exportBtn.addEventListener("click", () => {
                        try {
                            const payload = JSON.parse(decodeURIComponent(exportBtn.dataset.csvPayload));
                            window.downloadReportCSV(payload);
                        } catch (err) {
                            console.error("Failed to parse CSV payload:", err);
                        }
                    });
                }
            } else {
                bubble.innerHTML = window.frappe && frappe.markdown 
                    ? frappe.markdown(String(cleanText)) 
                    : this.escapeHtml(cleanText);
            }
        } else {
            bubble.textContent = cleanText;
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        container.appendChild(row);
        this.scrollToBottom();
    }

    showTyping() {
        if (this.typing) return;
        this.typing = true;

        const container = document.getElementById("erp-ai-messages");
        const row = document.createElement("div");
        row.className = "erp-ai-row assistant erp-ai-typing-row";

        const avatar = document.createElement("div");
        avatar.className = "erp-ai-avatar erp-ai-thinking";
        avatar.innerHTML = '<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';

        const bubble = document.createElement("div");
        bubble.className = "erp-ai-message assistant";
        bubble.innerHTML = `
            <div class="erp-ai-loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        row.appendChild(avatar);
        row.appendChild(bubble);
        container.appendChild(row);
        this.scrollToBottom();
    }

    hideTyping() {
        this.typing = false;
        const typingRow = document.querySelector(".erp-ai-typing-row");
        if (typingRow) typingRow.remove();
    }

    scrollToBottom() {
        const body = document.getElementById("erp-ai-body");
        if (body) {
            body.scrollTop = body.scrollHeight;
        }
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        new ERPAI();
    });
} else {
    new ERPAI();
}