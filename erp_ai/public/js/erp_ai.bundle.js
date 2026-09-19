class ERPAI {
    constructor() {
        if (window.__erpAiInstance) {
            console.warn("ERP AI: an instance is already running on this page.");
            return window.__erpAiInstance;
        }
        window.__erpAiInstance = this;

        this.cleanupDuplicates();

        this.messages = [];
        this.conversation = null;
        this.typing = false;
        this.dragging = false;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;
        this.attachedFileContent = null;
        this.attachedFileName = "";
        this.isRecording = false;

        this.resizing = false;
        this.resizeStartX = 0;
        this.resizeStartY = 0;
        this.resizeStartWidth = 0;
        this.resizeStartHeight = 0;
        this.minWidth = 400;
        this.minHeight = 520;
        this.isDarkMode = false;

        this.initSettingsAndTheme().then(() => {
            this.injectStyles();
            this.createButton();
            this.createWindow();
            this.applyTheme();
        });
    }

    cleanupDuplicates() {
        document.querySelectorAll("#erp-ai-window, #erp-ai-button, #erp-ai-styles").forEach(el => el.remove());
    }

    async initSettingsAndTheme() {
        return new Promise((resolve) => {
            if (typeof frappe !== "undefined" && frappe.db) {
                frappe.db.get_single_value("AI Settings", "dark_mode").then(val => {
                    this.isDarkMode = val ? true : false;
                    resolve();
                }).catch(() => {
                    this.isDarkMode = localStorage.getItem("erp_ai_dark_mode") === "true";
                    resolve();
                });
            } else {
                this.isDarkMode = localStorage.getItem("erp_ai_dark_mode") === "true";
                resolve();
            }
        });
    }

    injectStyles() {
        if (document.getElementById("erp-ai-styles")) return;

        const style = document.createElement("style");
        style.id = "erp-ai-styles";
        style.textContent = `
            :root {
                --erp-ink: #38322E;
                --erp-slate: #6B625B;
                --erp-border: #E8E2D9;
                --erp-surface: #FAF7F2;
                --erp-surface-soft: #F2EFE9;
                --erp-accent: #CC785C;
                --erp-accent-hover: #B8674B;
                --erp-accent-soft: #FCEFEA;
                --erp-danger: #D9534F;
                --erp-online: #528F65;
                --erp-ease: cubic-bezier(0.16, 1, 0.3, 1);
                --erp-shadow: 0 20px 25px -5px rgba(56, 50, 46, 0.08), 0 10px 10px -5px rgba(56, 50, 46, 0.03);
            }

            .erp-dark-theme {
                --erp-ink: #EDE8E1;
                --erp-slate: #A39B93;
                --erp-border: #3A3532;
                --erp-surface: #262321;
                --erp-surface-soft: #1E1B19;
                --erp-accent: #D98262;
                --erp-accent-hover: #E09575;
                --erp-accent-soft: rgba(217, 130, 98, 0.15);
                --erp-danger: #E57373;
                --erp-online: #66BB6A;
                --erp-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
            }

            #erp-ai-button {
                position: fixed;
                right: 24px;
                bottom: 24px;
                width: 62px;
                height: 62px;
                border-radius: 20px;
                background: linear-gradient(135deg, var(--erp-accent) 0%, #B8674B 100%);
                cursor: pointer;
                z-index: 9998;
                box-shadow: 0 14px 28px -6px rgba(204, 120, 92, 0.45);
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(255,255,255,0.25);
                animation: erp-float-pulse 3s ease-in-out infinite;
                transition: transform 250ms var(--erp-ease), box-shadow 250ms var(--erp-ease);
            }
            @keyframes erp-float-pulse {
                0% { transform: translateY(0) scale(1); box-shadow: 0 14px 28px -6px rgba(204, 120, 92, 0.45); }
                50% { transform: translateY(-6px) scale(1.04); box-shadow: 0 20px 36px -6px rgba(204, 120, 92, 0.6); }
                100% { transform: translateY(0) scale(1); box-shadow: 0 14px 28px -6px rgba(204, 120, 92, 0.45); }
            }
            #erp-ai-button:hover { 
                animation: none;
                transform: translateY(-6px) scale(1.08); 
                box-shadow: 0 22px 40px -6px rgba(204, 120, 92, 0.7); 
            }

            /* Animations inside the floating icon logo */
            .erp-logo-svg .erp-orbit-ring {
                transform-origin: 12px 12px;
                animation: erp-spin-slow 8s linear infinite;
            }
            .erp-logo-svg .erp-sparkle-1 {
                animation: erp-pulse-sparkle 2s ease-in-out infinite;
            }
            .erp-logo-svg .erp-sparkle-2 {
                animation: erp-pulse-sparkle 2s ease-in-out infinite 1s;
            }
            @keyframes erp-spin-slow {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            @keyframes erp-pulse-sparkle {
                0%, 100% { opacity: 0.3; transform: scale(0.8); }
                50% { opacity: 1; transform: scale(1.2); }
            }

            #erp-ai-window {
                position: fixed;
                right: 24px;
                bottom: 100px;
                width: 420px;
                height: 620px;
                border-radius: 24px;
                background: var(--erp-surface);
                box-shadow: var(--erp-shadow);
                border: 1px solid var(--erp-border);
                z-index: 9999;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                font-family: inherit;
                backdrop-filter: blur(12px);
                transition: background 200ms, border-color 200ms;
            }

            #erp-ai-header {
                padding: 14px 20px;
                background: var(--erp-surface);
                border-bottom: 1px solid var(--erp-border);
                display: flex;
                align-items: center;
                justify-content: space-between;
                cursor: grab;
                user-select: none;
            }
            #erp-ai-header:active { cursor: grabbing; }

            .erp-ai-icon-btn {
                border: none;
                background: transparent;
                border-radius: 8px;
                width: 32px;
                height: 32px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--erp-slate);
                transition: all 150ms var(--erp-ease);
            }
            .erp-ai-icon-btn:hover {
                background: var(--erp-surface-soft);
                color: var(--erp-ink);
            }

            .erp-ai-main-layout {
                display: flex;
                flex: 1;
                overflow: hidden;
                position: relative;
                width: 100%;
            }

            #erp-ai-sidebar {
                width: 0px;
                background: var(--erp-surface);
                border-right: 0px solid var(--erp-border);
                display: flex;
                flex-direction: column;
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                z-index: 40;
                overflow: hidden;
                visibility: hidden;
                pointer-events: none;
                transition: width 300ms var(--erp-ease), border-right-width 300ms var(--erp-ease), visibility 300ms;
            }

            #erp-ai-sidebar.open {
                width: 280px;
                border-right: 1px solid var(--erp-border);
                visibility: visible;
                pointer-events: auto;
                box-shadow: 10px 0 30px rgba(0,0,0,0.08);
            }

            .erp-ai-sidebar-header {
                padding: 14px;
                border-bottom: 1px solid var(--erp-border);
                min-width: 280px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .erp-ai-new-chat-btn {
                width: 100%;
                background: var(--erp-accent);
                color: #fff;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 200ms;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                box-shadow: 0 4px 12px rgba(204, 120, 92, 0.2);
            }
            .erp-ai-new-chat-btn:hover { background: var(--erp-accent-hover); transform: translateY(-1px); }

            .erp-ai-sidebar-settings-btn {
                width: 100%;
                background: var(--erp-surface-soft);
                color: var(--erp-ink);
                border: 1px solid var(--erp-border);
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 200ms;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .erp-ai-sidebar-settings-btn:hover {
                background: var(--erp-accent-soft);
                color: var(--erp-accent);
                border-color: var(--erp-accent);
                transform: translateY(-1px);
            }

            .erp-ai-sidebar-body {
                flex: 1;
                overflow-y: auto;
                padding: 10px;
                min-width: 280px;
            }

            .erp-ai-conv-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 12px;
                font-size: 13px;
                color: var(--erp-slate);
                border-radius: 10px;
                cursor: pointer;
                margin-bottom: 4px;
                transition: all 150ms;
            }
            .erp-ai-conv-item:hover { background: var(--erp-surface-soft); color: var(--erp-ink); }
            .erp-ai-conv-item.active { background: var(--erp-accent-soft); color: var(--erp-accent); font-weight: 600; }
            
            .erp-ai-conv-title {
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex: 1;
            }

            .erp-ai-delete-conv {
                background: none;
                border: none;
                color: var(--erp-slate);
                cursor: pointer;
                font-size: 13px;
                padding: 2px 6px;
                border-radius: 6px;
                opacity: 0;
                transition: opacity 150ms, color 150ms;
            }
            .erp-ai-conv-item:hover .erp-ai-delete-conv { opacity: 1; }
            .erp-ai-delete-conv:hover { color: var(--erp-danger); background: rgba(217, 83, 79, 0.1); }

            #erp-ai-body {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: var(--erp-surface-soft);
                display: flex;
                flex-direction: column;
                gap: 16px;
                user-select: text;
                width: 100%;
                box-sizing: border-box;
                scroll-behavior: smooth;
            }

            .erp-ai-suggestions {
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin-top: 16px;
                width: 100%;
            }
            .erp-ai-suggestion-chip {
                background: var(--erp-surface);
                border: 1px solid var(--erp-border);
                padding: 10px 14px;
                border-radius: 12px;
                font-size: 12px;
                color: var(--erp-ink);
                cursor: pointer;
                text-align: right;
                transition: all 200ms;
                box-shadow: 0 2px 4px rgba(0,0,0,0.01);
            }
            .erp-ai-suggestion-chip:hover {
                border-color: var(--erp-accent);
                background: var(--erp-accent-soft);
                color: var(--erp-accent);
                transform: translateY(-1px);
            }

            #erp-ai-footer {
                padding: 14px 18px;
                background: var(--erp-surface);
                border-top: 1px solid var(--erp-border);
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .erp-ai-file-chip {
                display: none;
                align-items: center;
                justify-content: space-between;
                font-size: 12px;
                color: var(--erp-accent);
                padding: 6px 12px;
                background: var(--erp-accent-soft);
                border-radius: 10px;
                border: 1px solid var(--erp-accent);
                animation: erp-fadeIn 200ms ease;
            }
            @keyframes erp-fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

            .erp-ai-input-wrapper {
                display: flex;
                align-items: center;
                gap: 8px;
                background: var(--erp-surface-soft);
                border: 1px solid var(--erp-border);
                border-radius: 16px;
                padding: 6px 10px;
                transition: all 200ms;
            }
            .erp-ai-input-wrapper:focus-within {
                border-color: var(--erp-accent);
                box-shadow: 0 0 0 3px var(--erp-accent-soft);
                background: var(--erp-surface);
            }

            #erp-ai-input {
                flex: 1;
                border: none;
                background: transparent;
                resize: none;
                outline: none;
                max-height: 120px;
                font-size: 13px;
                color: var(--erp-ink);
                line-height: 1.5;
                font-family: inherit;
                padding: 6px 0;
            }

            .erp-panel-action-btn {
                background: transparent;
                border: none;
                width: 34px;
                height: 34px;
                border-radius: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--erp-slate);
                transition: all 200ms var(--erp-ease);
                flex-shrink: 0;
            }
            .erp-panel-action-btn:hover {
                background: var(--erp-accent-soft);
                color: var(--erp-accent);
                transform: translateY(-1px);
            }

            #erp-ai-send {
                background: var(--erp-accent);
                color: #fff;
                border: none;
                width: 36px;
                height: 36px;
                border-radius: 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 200ms var(--erp-ease);
                box-shadow: 0 4px 10px rgba(204, 120, 92, 0.25);
                flex-shrink: 0;
            }
            #erp-ai-send:hover {
                background: var(--erp-accent-hover);
                transform: translateY(-1px) scale(1.04);
                box-shadow: 0 6px 14px rgba(204, 120, 92, 0.35);
            }

            .erp-ai-row { display: flex; gap: 12px; align-items: flex-start; width: 100%; position: relative; }
            .erp-ai-row.user { flex-direction: row-reverse; }

            .erp-ai-avatar {
                border-radius: 12px;
                background: var(--erp-accent-soft);
                width: 34px;
                height: 34px;
                flex-shrink: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 13px;
                font-weight: 700;
                color: var(--erp-accent);
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }

            .erp-ai-message-container {
                max-width: 80%;
                display: flex;
                flex-direction: column;
                gap: 4px;
            }
            .erp-ai-row.user .erp-ai-message-container { align-items: flex-end; }
            .erp-ai-row.assistant .erp-ai-message-container { align-items: flex-start; }

            .erp-ai-message {
                padding: 12px 16px;
                font-size: 13px;
                line-height: 1.5;
                word-break: normal;
                overflow-wrap: break-word;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            }
            .erp-ai-message.user {
                background: var(--erp-accent-soft);
                color: var(--erp-ink);
                border: 1px solid var(--erp-border);
                border-radius: 16px 16px 4px 16px;
                text-align: right;
                display: inline-block;
                width: fit-content;
                max-width: 100%;
                word-wrap: break-word;
            }
            .erp-ai-message.assistant {
                background: var(--erp-surface);
                color: var(--erp-ink);
                border: 1px solid var(--erp-border);
                border-radius: 16px 16px 18px 4px;
            }

            .erp-typing-cursor::after {
                content: '';
                display: inline-block;
                width: 6px;
                height: 13px;
                background: var(--erp-accent);
                margin-right: 4px;
                animation: erp-blink 0.8s infinite;
                vertical-align: middle;
            }
            @keyframes erp-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

            .erp-ai-msg-actions {
                display: flex;
                gap: 6px;
                opacity: 0;
                transition: opacity 150ms;
                font-size: 11px;
                padding: 0 4px;
            }
            .erp-ai-row:hover .erp-ai-msg-actions { opacity: 1; }
            .erp-ai-action-btn {
                background: var(--erp-surface);
                border: 1px solid var(--erp-border);
                color: var(--erp-slate);
                border-radius: 6px;
                padding: 2px 6px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 4px;
                transition: all 150ms;
            }
            .erp-ai-action-btn:hover { background: var(--erp-accent-soft); color: var(--erp-accent); border-color: var(--erp-accent); }

            .erp-ai-loading-dots {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 0;
            }
            .erp-ai-loading-dots span {
                width: 5px; 
                height: 5px; 
                border-radius: 50%; 
                background: var(--erp-slate);
                animation: erp-ai-dot-beat 1.1s ease-in-out infinite;
                opacity: 0.4;
            }
            .erp-ai-loading-dots span:nth-child(2) { animation-delay: 160ms; }
            .erp-ai-loading-dots span:nth-child(3) { animation-delay: 320ms; }
            @keyframes erp-ai-dot-beat {
                0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
                30% { transform: translateY(-3px); opacity: 1; }
            }

            .erp-mic-recording {
                color: var(--erp-danger) !important;
                background: rgba(217, 83, 79, 0.1) !important;
                border-color: var(--erp-danger) !important;
                animation: erp-pulse 1.2s infinite;
            }
            @keyframes erp-pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.7; transform: scale(1.08); } 100% { opacity: 1; transform: scale(1); } }

            #erp-ai-resize-handle {
                position: absolute;
                right: 0;
                bottom: 0;
                width: 18px;
                height: 18px;
                cursor: nwse-resize;
                z-index: 100;
                background: linear-gradient(135deg, transparent 50%, var(--erp-slate) 50%);
                opacity: 0.4;
                border-bottom-right-radius: 24px;
                transition: opacity 200ms;
            }
            #erp-ai-resize-handle:hover { opacity: 0.8; }
        `;
        document.head.appendChild(style);
    }

    createButton() {
        const button = document.createElement("div");
        button.id = "erp-ai-button";
        // Modern animated AI Brain/Neural core SVG icon with glowing nodes & rotating ring
        button.innerHTML = `
            <svg class="erp-logo-svg" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle class="erp-orbit-ring" cx="12" cy="12" r="9" stroke-dasharray="4 3" stroke-width="1.5" stroke="rgba(255,255,255,0.7)"></circle>
                <circle class="erp-sparkle-1" cx="12" cy="7" r="1.5" fill="#FFFFFF" stroke="none"></circle>
                <circle class="erp-sparkle-2" cx="16" cy="14" r="1.5" fill="#FFFFFF" stroke="none"></circle>
                <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0" stroke-width="2.2" fill="rgba(255,255,255,0.2)"></path>
                <path d="M9 12L6 15M15 12l3 3M12 9V6"></path>
            </svg>
        `;
        document.body.appendChild(button);
        button.addEventListener("click", () => this.toggleWindow());
    }

    createWindow() {
        if (document.getElementById("erp-ai-window")) return;

        const windowElement = document.createElement("div");
        windowElement.id = "erp-ai-window";
        windowElement.style.display = "none";

        windowElement.innerHTML = `
            <div id="erp-ai-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <button id="erp-ai-toggle-sidebar" class="erp-ai-icon-btn" title="Toggle History">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
                    </button>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 28px; height: 28px; background: var(--erp-accent-soft); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--erp-accent);">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="3" fill="var(--erp-accent)"></circle>
                                <path d="M12 2v3M12 19v3M2 12h3M19 12h3"></path>
                                <path d="M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"></path>
                            </svg>
                        </div>
                        <span style="font-weight: 700; font-size: 14px; color: var(--erp-ink); letter-spacing: -0.2px;">ERP Assistant</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <button id="erp-ai-minimize" class="erp-ai-icon-btn" title="Minimize" style="font-size:16px;">&#8211;</button>
                    <button id="erp-ai-close" class="erp-ai-icon-btn" title="Close" style="font-size:18px;">&times;</button>
                </div>
            </div>

            <div class="erp-ai-main-layout">
                <div id="erp-ai-sidebar">
                    <div class="erp-ai-sidebar-header">
                        <button id="erp-ai-new-chat" class="erp-ai-new-chat-btn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                            New Chat
                        </button>
                        <button id="erp-ai-settings-btn" class="erp-ai-sidebar-settings-btn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06-.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                            AI Settings
                        </button>
                    </div>
                    <div id="erp-ai-conversations-list" class="erp-ai-sidebar-body">
                        <div style="font-size: 12px; color: var(--erp-slate); text-align:center; padding-top:25px;">No conversations</div>
                    </div>
                </div>

                <div id="erp-ai-body">
                    <div id="erp-ai-welcome" style="text-align: center; margin-top: 40px; color: var(--erp-slate);">
                        <div style="font-size: 32px; margin-bottom: 8px; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1));">✨</div>
                        <div style="font-weight: 700; font-size: 16px; color: var(--erp-ink); letter-spacing: -0.3px;">How can I help you today?</div>
                        <div style="font-size: 12px; margin-top: 6px; max-width: 260px; margin-left: auto; margin-right: auto; line-height: 1.4;">Ask questions about records, generate reports, or manage your workflow.</div>
                        
                        <div class="erp-ai-suggestions">
                            <div class="erp-ai-suggestion-chip" data-prompt="اعرض لي تقرير المبيعات اليومية">📊 اعرض لي تقرير المبيعات اليومية</div>
                            <div class="erp-ai-suggestion-chip" data-prompt="ما هي الفواتير المتأخرة غير المسددة؟">🧾 ما هي الفواتير المتأخرة غير المسددة؟</div>
                            <div class="erp-ai-suggestion-chip" data-prompt="قم بإنشاء لوحة تحكم جديدة للمبيعات">📈 قم بإنشاء لوحة تحكم جديدة للمبيعات</div>
                        </div>
                    </div>
                    <div id="erp-ai-messages" style="display:flex; flex-direction:column; gap:16px;"></div>
                </div>
            </div>

            <div id="erp-ai-footer">
                <div id="erp-ai-file-preview" class="erp-ai-file-chip">
                    <span id="erp-ai-file-name-text">📎 attached_file.txt</span>
                    <button id="erp-ai-remove-file" style="border:none; background:none; cursor:pointer; font-weight:bold; color:var(--erp-accent); font-size:14px;">&times;</button>
                </div>
                <div class="erp-ai-input-wrapper">
                    <input type="file" id="erp-ai-file-input" accept="image/*,.txt,.pdf,.csv" style="display:none;">
                    <button id="erp-ai-attach-btn" class="erp-panel-action-btn" title="Attach file or image">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
                    </button>
                    <button id="erp-ai-mic-btn" class="erp-panel-action-btn" title="Voice recording">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v1a7 7 0 0 1-14 0v-1"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
                    </button>
                    <textarea id="erp-ai-input" rows="1" placeholder="Type a message or use mic..."></textarea>
                    <button id="erp-ai-send" title="Send message">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </div>
            </div>
            <div id="erp-ai-resize-handle"></div>
        `;

        document.body.appendChild(windowElement);

        this.setupResizableWindow();
        this.bindEvents();
        this.applyTheme();
    }

    applyTheme() {
        const win = document.getElementById("erp-ai-window");
        if (!win) return;

        if (this.isDarkMode) {
            win.classList.add("erp-dark-theme");
        } else {
            win.classList.remove("erp-dark-theme");
        }
        localStorage.setItem("erp_ai_dark_mode", this.isDarkMode);
    }

    setupResizableWindow() {
        const windowEl = document.getElementById("erp-ai-window");
        const handle = document.getElementById("erp-ai-resize-handle");
        if (!windowEl || !handle) return;

        windowEl.style.minWidth = this.minWidth + "px";
        windowEl.style.minHeight = this.minHeight + "px";

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

        document.addEventListener("mousemove", (e) => {
            if (!this.resizing) return;
            let newWidth = this.resizeStartWidth + (e.clientX - this.resizeStartX);
            let newHeight = this.resizeStartHeight + (e.clientY - this.resizeStartY);

            windowEl.style.width = Math.min(Math.max(newWidth, this.minWidth), window.innerWidth * 0.95) + "px";
            windowEl.style.height = Math.min(Math.max(newHeight, this.minHeight), window.innerHeight * 0.90) + "px";
        });

        document.addEventListener("mouseup", () => {
            if (this.resizing) {
                this.resizing = false;
                document.body.style.userSelect = "";
            }
        });
    }

    bindEvents() {
        const input = document.getElementById("erp-ai-input");
        const closeBtn = document.getElementById("erp-ai-close");
        const minimizeBtn = document.getElementById("erp-ai-minimize");
        const sendBtn = document.getElementById("erp-ai-send");
        const settingsBtn = document.getElementById("erp-ai-settings-btn");
        const micBtn = document.getElementById("erp-ai-mic-btn");

        if (closeBtn) closeBtn.addEventListener("click", () => this.hideWindow());
        if (minimizeBtn) minimizeBtn.addEventListener("click", () => this.hideWindow());
        if (sendBtn) sendBtn.addEventListener("click", () => this.sendMessage());
        
        if (settingsBtn) {
            settingsBtn.addEventListener("click", () => {
                if (typeof frappe !== "undefined" && typeof frappe.set_route === "function") {
                    frappe.set_route("Form", "AI Settings");
                } else {
                    console.warn("Frappe router not available.");
                }
            });
        }

        if (micBtn) {
            let mediaRecorder;
            let audioChunks = [];

            micBtn.addEventListener("click", async () => {
                if (!this.isRecording) {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);
                        audioChunks = [];

                        mediaRecorder.ondataavailable = (event) => {
                            if (event.data.size > 0) audioChunks.push(event.data);
                        };

                        mediaRecorder.onstop = async () => {
                            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                            
                            const reader = new FileReader();
                            reader.onloadend = () => {
                                this.attachedFileContent = reader.result;
                                this.attachedFileName = `voice_note_${Date.now()}.webm`;
                                
                                const preview = document.getElementById("erp-ai-file-preview");
                                const nameText = document.getElementById("erp-ai-file-name-text");
                                if (preview && nameText) {
                                    preview.style.display = "flex";
                                    nameText.textContent = `🎤 رسالة صوتية مسجلة`;
                                }
                                
                                this.sendMessage("قم بتفريغ هذه الرسالة الصوتية وتنفيذ الطلب الموجود فيها");
                            };
                            reader.readAsDataURL(audioBlob);

                            stream.getTracks().forEach(track => track.stop());
                        };

                        mediaRecorder.start();
                        this.isRecording = true;
                        micBtn.classList.add("erp-mic-recording");
                        if (typeof frappe !== "undefined" && typeof frappe.show_alert === "function") {
                            frappe.show_alert({message: "جاري التسجيل... اضغط مرة أخرى للإيقاف", indicator: "blue"});
                        }
                    } catch (err) {
                        console.error("Microphone access error:", err);
                        alert("لا يمكن الوصول إلى الميكروفون. تأكد من إعطاء الصلاحية أو استخدام HTTPS.");
                    }
                } else {
                    if (mediaRecorder && mediaRecorder.state !== "inactive") {
                        mediaRecorder.stop();
                    }
                    this.isRecording = false;
                    micBtn.classList.remove("erp-mic-recording");
                }
            });
        }

        if (input) {
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            input.addEventListener("input", function() {
                this.style.height = "auto";
                this.style.height = Math.min(this.scrollHeight, 120) + "px";
            });
        }

        const welcomeContainer = document.getElementById("erp-ai-welcome");
        if (welcomeContainer) {
            welcomeContainer.addEventListener("click", (e) => {
                const chip = e.target.closest(".erp-ai-suggestion-chip");
                if (chip && chip.dataset.prompt) {
                    const inputEl = document.getElementById("erp-ai-input");
                    if (inputEl) {
                        inputEl.value = chip.dataset.prompt;
                        this.sendMessage();
                    }
                }
            });
        }

        const fileInput = document.getElementById("erp-ai-file-input");
        const attachBtn = document.getElementById("erp-ai-attach-btn");
        const removeFileBtn = document.getElementById("erp-ai-remove-file");

        if (attachBtn && fileInput) {
            attachBtn.addEventListener("click", () => fileInput.click());
            fileInput.addEventListener("change", (e) => {
                const file = e.target.files[0];
                if (!file) return;
                this.attachedFileName = file.name;
                
                const reader = new FileReader();
                reader.onload = (event) => {
                    this.attachedFileContent = event.target.result;
                    let preview = document.getElementById("erp-ai-file-preview");
                    let nameText = document.getElementById("erp-ai-file-name-text");
                    if (preview && nameText) {
                        preview.style.display = "flex";
                        nameText.textContent = `📎 ${this.attachedFileName}`;
                    }
                };

                if (file.type.startsWith("image/")) {
                    reader.readAsDataURL(file);
                } else {
                    reader.readAsText(file);
                }
            });
        }

        if (removeFileBtn) {
            removeFileBtn.addEventListener("click", () => {
                this.attachedFileContent = null;
                this.attachedFileName = "";
                const preview = document.getElementById("erp-ai-file-preview");
                if (preview) preview.style.display = "none";
                if (fileInput) fileInput.value = "";
            });
        }

        const toggleSidebarBtn = document.getElementById("erp-ai-toggle-sidebar");
        const sidebar = document.getElementById("erp-ai-sidebar");
        if (toggleSidebarBtn && sidebar) {
            toggleSidebarBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                sidebar.classList.toggle("open");
                if (sidebar.classList.contains("open")) {
                    this.loadConversationsList();
                }
            });
        }

        const newChatBtn = document.getElementById("erp-ai-new-chat");
        if (newChatBtn) newChatBtn.addEventListener("click", () => this.startNewChat());

        const conversationsList = document.getElementById("erp-ai-conversations-list");
        if (conversationsList) {
            conversationsList.addEventListener("click", (e) => {
                const deleteBtn = e.target.closest(".erp-ai-delete-conv");
                if (deleteBtn) {
                    e.stopPropagation();
                    const item = deleteBtn.closest(".erp-ai-conv-item");
                    if (item && item.dataset.name) {
                        this.deleteConversation(item.dataset.name, item);
                    }
                    return;
                }

                const item = e.target.closest(".erp-ai-conv-item");
                if (item && item.dataset.name) {
                    this.loadConversationHistory(item.dataset.name);
                    if (sidebar) sidebar.classList.remove("open");
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
        const sidebar = document.getElementById("erp-ai-sidebar");
        if (sidebar) sidebar.classList.remove("open");
    }

    loadConversationsList() {
        const listEl = document.getElementById("erp-ai-conversations-list");
        if (!listEl || typeof frappe === "undefined") return;

        frappe.call({
            method: "erp_ai.api.get_user_conversations",
            callback: (r) => {
                const data = (r.message && r.message.status === "success") ? r.message.data : [];
                if (!data || data.length === 0) {
                    listEl.innerHTML = '<div style="font-size: 12px; color: var(--erp-slate); text-align:center; padding-top:25px;">No conversations</div>';
                    return;
                }
                listEl.innerHTML = "";
                data.forEach(c => {
                    const item = document.createElement("div");
                    item.className = "erp-ai-conv-item" + (c.name === this.conversation ? " active" : "");
                    item.dataset.name = c.name;
                    item.innerHTML = `
                        <span class="erp-ai-conv-title">${this.escapeHtml(c.title || c.name)}</span>
                        <button class="erp-ai-delete-conv" title="Delete chat">🗑️</button>
                    `;
                    listEl.appendChild(item);
                });
            }
        });
    }

    deleteConversation(conversationName, itemElement) {
        if (typeof frappe === "undefined") return;
        itemElement.style.opacity = "0.4";
        
        frappe.call({
            method: "erp_ai.api.delete_conversation",
            args: { conversation_name: conversationName },
            callback: (r) => {
                if (r.message && r.message.status === "success") {
                    itemElement.remove();
                    if (this.conversation === conversationName) this.startNewChat();
                    if (typeof frappe.show_alert === "function") {
                        frappe.show_alert({message: "Conversation deleted successfully", indicator: "green"});
                    }
                } else {
                    itemElement.style.opacity = "1";
                }
            },
            error: () => { itemElement.style.opacity = "1"; }
        });
    }

    loadConversationHistory(conversationName) {
        if (typeof frappe === "undefined") return;
        frappe.call({
            method: "erp_ai.api.load_conversation",
            args: { conversation_name: conversationName },
            callback: (r) => {
                if (!r.message || r.message.status !== "success") return;
                this.conversation = r.message.name;
                this.messages = Array.isArray(r.message.messages) ? r.message.messages : [];

                const container = document.getElementById("erp-ai-messages");
                if (container) container.innerHTML = "";
                const welcome = document.getElementById("erp-ai-welcome");
                if (welcome) welcome.style.display = "none";

                this.messages.forEach(m => this.addMessage(m.content, m.role === "user" ? "user" : "assistant", false));
                this.loadConversationsList();
            }
        });
    }

    enableDragging() {
        const windowEl = document.getElementById("erp-ai-window");
        const header = document.getElementById("erp-ai-header");
        if (!windowEl || !header) return;

        windowEl.addEventListener("dragstart", (e) => e.preventDefault(), true);
        header.addEventListener("dragstart", (e) => e.preventDefault(), true);

        header.addEventListener("mousedown", (e) => {
            if (e.target.tagName === "BUTTON" || e.target.closest("button")) return;
            e.preventDefault();

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
        const win = document.getElementById("erp-ai-window");
        if (win) win.style.display = "flex";
    }

    hideWindow() {
        const win = document.getElementById("erp-ai-window");
        if (win) win.style.display = "none";
    }

    toggleWindow() {
        const win = document.getElementById("erp-ai-window");
        if (win) {
            win.style.display === "flex" ? this.hideWindow() : this.showWindow();
        }
    }

    scrollToBottom() {
        const body = document.getElementById("erp-ai-body");
        if (body) body.scrollTop = body.scrollHeight;
    }

    async sendMessage(overrideMessage = null) {
        const input = document.getElementById("erp-ai-input");
        const message = overrideMessage !== null ? overrideMessage : (input ? input.value.trim() : "");
        if (!message && !this.attachedFileContent) return;

        if (input && overrideMessage === null) {
            input.value = "";
            input.style.height = "auto";
        }

        const welcome = document.getElementById("erp-ai-welcome");
        if (welcome) welcome.style.display = "none";

        let displayMessage = message;
        if (this.attachedFileName) displayMessage += `\n[مرفق: ${this.attachedFileName}]`;

        this.messages.push({ role: "user", content: message });
        this.addMessage(displayMessage, "user", false);

        let argsPayload = {
            message: message || "قم بتحليل هذا الملف المرفق",
            conversation: JSON.stringify(this.messages.slice(0, -1)),
            conversation_name: this.conversation
        };

        if (this.attachedFileContent) {
            argsPayload.file_data = this.attachedFileContent;
            argsPayload.file_name = this.attachedFileName;
        }

        this.attachedFileContent = null;
        this.attachedFileName = "";
        const preview = document.getElementById("erp-ai-file-preview");
        if (preview) preview.style.display = "none";

        this.showTyping();

        try {
            if (typeof frappe === "undefined") throw new Error("Frappe framework not detected.");

            const response = await frappe.call({
                method: "erp_ai.api.ask",
                args: argsPayload
            });

            this.hideTyping();

            if (response && response.message && response.message.reply) {
                if (response.message.conversation_name) {
                    this.conversation = response.message.conversation_name;
                }
                let reply = response.message.reply;
                if (Array.isArray(reply)) reply = reply.join("");

                this.addMessage(reply, "assistant", true); 
                this.messages.push({ role: "assistant", content: reply });
                
                const sidebar = document.getElementById("erp-ai-sidebar");
                if (sidebar && sidebar.classList.contains("open")) {
                    this.loadConversationsList();
                }
            } else {
                this.addMessage("No response received from AI.", "assistant", false);
            }
        } catch (e) {
            console.error(e);
            this.hideTyping();
            this.addMessage("Something went wrong.", "assistant", false);
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
                headers.forEach((h, idx) => { rowObj[h] = cells[idx] !== undefined ? cells[idx] : ""; });
                data.push(rowObj);
            }
            return data.length > 0 ? data : null;
        } catch (e) {
            return null;
        }
    }

    escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value === undefined || value === null ? "" : String(value);
        return div.innerHTML;
    }

    renderContent(bubble, cleanText, isStreaming, onComplete) {
        const tableData = this.extractTableData(cleanText);
        if (tableData && tableData.length > 0) {
            let textParts = cleanText.split(/\|.*\|/);
            let textWithoutTable = textParts[0] ? textParts[0].trim() : "";

            let htmlOutput = `<div class="erp-text-content" style="margin-bottom: 10px;">${window.frappe && frappe.markdown ? frappe.markdown(textWithoutTable) : this.escapeHtml(textWithoutTable)}</div>`;
            htmlOutput += `<div style="overflow-x:auto; margin: 10px 0; border-radius: 8px; border: 1px solid var(--erp-border);"><table style="width:100%; border-collapse:collapse; font-size:12px; background:var(--erp-surface);"><tr style="background:var(--erp-surface-soft);">`;
            
            let headers = Object.keys(tableData[0]);
            headers.forEach(h => { htmlOutput += `<th style="padding:8px 10px; border-bottom:1px solid var(--erp-border); text-align:left; color:var(--erp-ink);">${this.escapeHtml(h)}</th>`; });
            htmlOutput += `</tr>`;

            tableData.forEach(row => {
                htmlOutput += `<tr>`;
                headers.forEach(h => { htmlOutput += `<td style="padding:8px 10px; border-bottom:1px solid var(--erp-border); color:var(--erp-ink);">${this.escapeHtml(row[h] || '')}</td>`; });
                htmlOutput += `</tr>`;
            });
            htmlOutput += `</table></div>`;

            let encodedData = encodeURIComponent(JSON.stringify(tableData));
            htmlOutput += `<button type="button" class="export-csv-btn" data-csv-payload="${encodedData}" style="cursor:pointer; background:var(--erp-surface-soft); border:1px solid var(--erp-border); color:var(--erp-ink); border-radius:8px; padding:8px; font-size:12px; font-weight:600; width:100%; margin-top:8px; transition: background 150ms;">⬇ Download (CSV)</button>`;

            bubble.innerHTML = htmlOutput;
            const exportBtn = bubble.querySelector(".export-csv-btn");
            if (exportBtn) {
                exportBtn.addEventListener("click", () => {
                    try {
                        const payload = JSON.parse(decodeURIComponent(exportBtn.dataset.csvPayload));
                        this.downloadFallbackCSV(payload);
                    } catch (err) { console.error(err); }
                });
            }
            if (onComplete) onComplete();
        } else {
            if (isStreaming) {
                bubble.classList.add("erp-typing-cursor");
                let i = 0;
                const speed = 12; 
                const textLength = cleanText.length;
                
                const typeInterval = setInterval(() => {
                    if (i < textLength) {
                        let currentSubstr = cleanText.substring(0, i + 1);
                        bubble.innerHTML = window.frappe && frappe.markdown ? frappe.markdown(currentSubstr) : this.escapeHtml(currentSubstr);
                        i++;
                        this.scrollToBottom();
                    } else {
                        clearInterval(typeInterval);
                        bubble.classList.remove("erp-typing-cursor");
                        bubble.innerHTML = window.frappe && frappe.markdown ? frappe.markdown(cleanText) : this.escapeHtml(cleanText);
                        if (onComplete) onComplete();
                    }
                }, speed);
            } else {
                bubble.innerHTML = window.frappe && frappe.markdown ? frappe.markdown(cleanText) : this.escapeHtml(cleanText);
                if (onComplete) onComplete();
            }
        }
    }

    addMessage(text, sender, isStreaming = false) {
        const container = document.getElementById("erp-ai-messages");
        if (!container) return;

        const row = document.createElement("div");
        row.className = "erp-ai-row " + sender;

        const avatar = document.createElement("div");
        avatar.className = "erp-ai-avatar";
        avatar.textContent = sender === "user" ? "👤" : "AI";

        const msgContainer = document.createElement("div");
        msgContainer.className = "erp-ai-message-container";

        const bubble = document.createElement("div");
        bubble.className = "erp-ai-message " + sender;

        let cleanText = String(text).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g, "").trim();

        if (sender === "assistant") {
            const actionsToolbar = document.createElement("div");
            actionsToolbar.className = "erp-ai-msg-actions";
            actionsToolbar.innerHTML = `
                <button class="erp-ai-action-btn erp-copy-btn" title="Copy text">📋 Copy</button>
                <button class="erp-ai-action-btn erp-regen-btn" title="Regenerate response">🔄 Regenerate</button>
            `;

            actionsToolbar.querySelector(".erp-copy-btn").addEventListener("click", () => {
                navigator.clipboard.writeText(cleanText).then(() => {
                    if (typeof frappe !== "undefined" && typeof frappe.show_alert === "function") {
                        frappe.show_alert({message: "Copied to clipboard", indicator: "green"});
                    } else {
                        alert("Copied to clipboard");
                    }
                }).catch(err => {
                    console.error("Failed to copy text: ", err);
                });
            });

            actionsToolbar.querySelector(".erp-regen-btn").addEventListener("click", () => {
                if (this.messages.length >= 2) {
                    this.messages.pop();
                    const lastUserMsg = this.messages.pop();
                    if (lastUserMsg) {
                        row.remove();
                        this.sendMessage(lastUserMsg.content);
                    }
                }
            });

            this.renderContent(bubble, cleanText, isStreaming, () => {
                this.scrollToBottom();
            });

            msgContainer.appendChild(bubble);
            msgContainer.appendChild(actionsToolbar);
        } else {
            bubble.textContent = cleanText;
            msgContainer.appendChild(bubble);
        }

        row.appendChild(avatar);
        row.appendChild(msgContainer);
        container.appendChild(row);
        this.scrollToBottom();
    }

    downloadFallbackCSV(data) {
        if (!data || !data.length) return;
        const headers = Object.keys(data[0]);
        let csv = headers.join(",") + "\n";
        data.forEach(row => {
            csv += headers.map(h => `"${(row[h] || "").toString().replace(/"/g, '""')}"`).join(",") + "\n";
        });
        const blob = new Blob(["\uFEFF" + csv], { type: "text/css;charset=utf-8;" }); // Fixed mime type setup
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `report_${Date.now()}.csv`;
        link.click();
    }

    showTyping() {
        if (this.typing) return;
        this.typing = true;
        const container = document.getElementById("erp-ai-messages");
        if (!container) return;

        const row = document.createElement("div");
        row.className = "erp-ai-row assistant erp-ai-typing-row";
        row.innerHTML = `
            <div class="erp-ai-avatar">AI</div>
            <div class="erp-ai-message-container">
                <div class="erp-ai-loading-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        container.append(row);
        this.scrollToBottom();
    }

    hideTyping() {
        this.typing, this.typing = false;
        const typingRow = document.querySelector(".erp-ai-typing-row");
        if (typingRow) typingRow.remove();
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => new ERPAI());
} else {
    new ERPAI();
}
