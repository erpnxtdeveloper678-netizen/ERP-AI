(()=>{var b=class{constructor(){if(window.__erpAiInstance)return console.warn("ERP AI: an instance is already running on this page."),window.__erpAiInstance;window.__erpAiInstance=this,this.cleanupDuplicates(),this.messages=[],this.conversation=null,this.typing=!1,this.dragging=!1,this.dragOffsetX=0,this.dragOffsetY=0,this.attachedFileContent=null,this.attachedFileName="",this.isRecording=!1,this.resizing=!1,this.resizeStartX=0,this.resizeStartY=0,this.resizeStartWidth=0,this.resizeStartHeight=0,this.minWidth=400,this.minHeight=520,this.isDarkMode=!1,this.initSettingsAndTheme().then(()=>{this.injectStyles(),this.createButton(),this.createWindow(),this.applyTheme()})}cleanupDuplicates(){document.querySelectorAll("#erp-ai-window, #erp-ai-button, #erp-ai-styles").forEach(e=>e.remove())}async initSettingsAndTheme(){return new Promise(e=>{typeof frappe!="undefined"&&frappe.db?frappe.db.get_single_value("AI Settings","dark_mode").then(t=>{this.isDarkMode=!!t,e()}).catch(()=>{this.isDarkMode=localStorage.getItem("erp_ai_dark_mode")==="true",e()}):(this.isDarkMode=localStorage.getItem("erp_ai_dark_mode")==="true",e())})}injectStyles(){if(document.getElementById("erp-ai-styles"))return;let e=document.createElement("style");e.id="erp-ai-styles",e.textContent=`
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
        `,document.head.appendChild(e)}createButton(){let e=document.createElement("div");e.id="erp-ai-button",e.innerHTML=`
            <svg class="erp-logo-svg" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle class="erp-orbit-ring" cx="12" cy="12" r="9" stroke-dasharray="4 3" stroke-width="1.5" stroke="rgba(255,255,255,0.7)"></circle>
                <circle class="erp-sparkle-1" cx="12" cy="7" r="1.5" fill="#FFFFFF" stroke="none"></circle>
                <circle class="erp-sparkle-2" cx="16" cy="14" r="1.5" fill="#FFFFFF" stroke="none"></circle>
                <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0" stroke-width="2.2" fill="rgba(255,255,255,0.2)"></path>
                <path d="M9 12L6 15M15 12l3 3M12 9V6"></path>
            </svg>
        `,document.body.appendChild(e),e.addEventListener("click",()=>this.toggleWindow())}createWindow(){if(document.getElementById("erp-ai-window"))return;let e=document.createElement("div");e.id="erp-ai-window",e.style.display="none",e.innerHTML=`
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
                        <div style="font-size: 32px; margin-bottom: 8px; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1));">\u2728</div>
                        <div style="font-weight: 700; font-size: 16px; color: var(--erp-ink); letter-spacing: -0.3px;">How can I help you today?</div>
                        <div style="font-size: 12px; margin-top: 6px; max-width: 260px; margin-left: auto; margin-right: auto; line-height: 1.4;">Ask questions about records, generate reports, or manage your workflow.</div>
                        
                        <div class="erp-ai-suggestions">
                            <div class="erp-ai-suggestion-chip" data-prompt="\u0627\u0639\u0631\u0636 \u0644\u064A \u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0645\u0628\u064A\u0639\u0627\u062A \u0627\u0644\u064A\u0648\u0645\u064A\u0629">\u{1F4CA} \u0627\u0639\u0631\u0636 \u0644\u064A \u062A\u0642\u0631\u064A\u0631 \u0627\u0644\u0645\u0628\u064A\u0639\u0627\u062A \u0627\u0644\u064A\u0648\u0645\u064A\u0629</div>
                            <div class="erp-ai-suggestion-chip" data-prompt="\u0645\u0627 \u0647\u064A \u0627\u0644\u0641\u0648\u0627\u062A\u064A\u0631 \u0627\u0644\u0645\u062A\u0623\u062E\u0631\u0629 \u063A\u064A\u0631 \u0627\u0644\u0645\u0633\u062F\u062F\u0629\u061F">\u{1F9FE} \u0645\u0627 \u0647\u064A \u0627\u0644\u0641\u0648\u0627\u062A\u064A\u0631 \u0627\u0644\u0645\u062A\u0623\u062E\u0631\u0629 \u063A\u064A\u0631 \u0627\u0644\u0645\u0633\u062F\u062F\u0629\u061F</div>
                            <div class="erp-ai-suggestion-chip" data-prompt="\u0642\u0645 \u0628\u0625\u0646\u0634\u0627\u0621 \u0644\u0648\u062D\u0629 \u062A\u062D\u0643\u0645 \u062C\u062F\u064A\u062F\u0629 \u0644\u0644\u0645\u0628\u064A\u0639\u0627\u062A">\u{1F4C8} \u0642\u0645 \u0628\u0625\u0646\u0634\u0627\u0621 \u0644\u0648\u062D\u0629 \u062A\u062D\u0643\u0645 \u062C\u062F\u064A\u062F\u0629 \u0644\u0644\u0645\u0628\u064A\u0639\u0627\u062A</div>
                        </div>
                    </div>
                    <div id="erp-ai-messages" style="display:flex; flex-direction:column; gap:16px;"></div>
                </div>
            </div>

            <div id="erp-ai-footer">
                <div id="erp-ai-file-preview" class="erp-ai-file-chip">
                    <span id="erp-ai-file-name-text">\u{1F4CE} attached_file.txt</span>
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
        `,document.body.appendChild(e),this.setupResizableWindow(),this.bindEvents(),this.applyTheme()}applyTheme(){let e=document.getElementById("erp-ai-window");!e||(this.isDarkMode?e.classList.add("erp-dark-theme"):e.classList.remove("erp-dark-theme"),localStorage.setItem("erp_ai_dark_mode",this.isDarkMode))}setupResizableWindow(){let e=document.getElementById("erp-ai-window"),t=document.getElementById("erp-ai-resize-handle");!e||!t||(e.style.minWidth=this.minWidth+"px",e.style.minHeight=this.minHeight+"px",t.addEventListener("mousedown",i=>{i.preventDefault(),i.stopPropagation(),this.resizing=!0;let a=e.getBoundingClientRect();this.resizeStartX=i.clientX,this.resizeStartY=i.clientY,this.resizeStartWidth=a.width,this.resizeStartHeight=a.height,document.body.style.userSelect="none"}),document.addEventListener("mousemove",i=>{if(!this.resizing)return;let a=this.resizeStartWidth+(i.clientX-this.resizeStartX),n=this.resizeStartHeight+(i.clientY-this.resizeStartY);e.style.width=Math.min(Math.max(a,this.minWidth),window.innerWidth*.95)+"px",e.style.height=Math.min(Math.max(n,this.minHeight),window.innerHeight*.9)+"px"}),document.addEventListener("mouseup",()=>{this.resizing&&(this.resizing=!1,document.body.style.userSelect="")}))}bindEvents(){let e=document.getElementById("erp-ai-input"),t=document.getElementById("erp-ai-close"),i=document.getElementById("erp-ai-minimize"),a=document.getElementById("erp-ai-send"),n=document.getElementById("erp-ai-settings-btn"),o=document.getElementById("erp-ai-mic-btn");if(t&&t.addEventListener("click",()=>this.hideWindow()),i&&i.addEventListener("click",()=>this.hideWindow()),a&&a.addEventListener("click",()=>this.sendMessage()),n&&n.addEventListener("click",()=>{typeof frappe!="undefined"&&typeof frappe.set_route=="function"?frappe.set_route("Form","AI Settings"):console.warn("Frappe router not available.")}),o){let p,c=[];o.addEventListener("click",async()=>{if(this.isRecording)p&&p.state!=="inactive"&&p.stop(),this.isRecording=!1,o.classList.remove("erp-mic-recording");else try{let g=await navigator.mediaDevices.getUserMedia({audio:!0});p=new MediaRecorder(g),c=[],p.ondataavailable=f=>{f.data.size>0&&c.push(f.data)},p.onstop=async()=>{let f=new Blob(c,{type:"audio/webm"}),v=new FileReader;v.onloadend=()=>{this.attachedFileContent=v.result,this.attachedFileName=`voice_note_${Date.now()}.webm`;let u=document.getElementById("erp-ai-file-preview"),w=document.getElementById("erp-ai-file-name-text");u&&w&&(u.style.display="flex",w.textContent="\u{1F3A4} \u0631\u0633\u0627\u0644\u0629 \u0635\u0648\u062A\u064A\u0629 \u0645\u0633\u062C\u0644\u0629"),this.sendMessage("\u0642\u0645 \u0628\u062A\u0641\u0631\u064A\u063A \u0647\u0630\u0647 \u0627\u0644\u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u0635\u0648\u062A\u064A\u0629 \u0648\u062A\u0646\u0641\u064A\u0630 \u0627\u0644\u0637\u0644\u0628 \u0627\u0644\u0645\u0648\u062C\u0648\u062F \u0641\u064A\u0647\u0627")},v.readAsDataURL(f),g.getTracks().forEach(u=>u.stop())},p.start(),this.isRecording=!0,o.classList.add("erp-mic-recording"),typeof frappe!="undefined"&&typeof frappe.show_alert=="function"&&frappe.show_alert({message:"\u062C\u0627\u0631\u064A \u0627\u0644\u062A\u0633\u062C\u064A\u0644... \u0627\u0636\u063A\u0637 \u0645\u0631\u0629 \u0623\u062E\u0631\u0649 \u0644\u0644\u0625\u064A\u0642\u0627\u0641",indicator:"blue"})}catch(g){console.error("Microphone access error:",g),alert("\u0644\u0627 \u064A\u0645\u0643\u0646 \u0627\u0644\u0648\u0635\u0648\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u064A\u0643\u0631\u0648\u0641\u0648\u0646. \u062A\u0623\u0643\u062F \u0645\u0646 \u0625\u0639\u0637\u0627\u0621 \u0627\u0644\u0635\u0644\u0627\u062D\u064A\u0629 \u0623\u0648 \u0627\u0633\u062A\u062E\u062F\u0627\u0645 HTTPS.")}})}e&&(e.addEventListener("keydown",p=>{p.key==="Enter"&&!p.shiftKey&&(p.preventDefault(),this.sendMessage())}),e.addEventListener("input",function(){this.style.height="auto",this.style.height=Math.min(this.scrollHeight,120)+"px"}));let s=document.getElementById("erp-ai-welcome");s&&s.addEventListener("click",p=>{let c=p.target.closest(".erp-ai-suggestion-chip");if(c&&c.dataset.prompt){let g=document.getElementById("erp-ai-input");g&&(g.value=c.dataset.prompt,this.sendMessage())}});let r=document.getElementById("erp-ai-file-input"),d=document.getElementById("erp-ai-attach-btn"),l=document.getElementById("erp-ai-remove-file");d&&r&&(d.addEventListener("click",()=>r.click()),r.addEventListener("change",p=>{let c=p.target.files[0];if(!c)return;this.attachedFileName=c.name;let g=new FileReader;g.onload=f=>{this.attachedFileContent=f.target.result;let v=document.getElementById("erp-ai-file-preview"),u=document.getElementById("erp-ai-file-name-text");v&&u&&(v.style.display="flex",u.textContent=`\u{1F4CE} ${this.attachedFileName}`)},c.type.startsWith("image/")?g.readAsDataURL(c):g.readAsText(c)})),l&&l.addEventListener("click",()=>{this.attachedFileContent=null,this.attachedFileName="";let p=document.getElementById("erp-ai-file-preview");p&&(p.style.display="none"),r&&(r.value="")});let h=document.getElementById("erp-ai-toggle-sidebar"),m=document.getElementById("erp-ai-sidebar");h&&m&&h.addEventListener("click",p=>{p.stopPropagation(),m.classList.toggle("open"),m.classList.contains("open")&&this.loadConversationsList()});let x=document.getElementById("erp-ai-new-chat");x&&x.addEventListener("click",()=>this.startNewChat());let y=document.getElementById("erp-ai-conversations-list");y&&y.addEventListener("click",p=>{let c=p.target.closest(".erp-ai-delete-conv");if(c){p.stopPropagation();let f=c.closest(".erp-ai-conv-item");f&&f.dataset.name&&this.deleteConversation(f.dataset.name,f);return}let g=p.target.closest(".erp-ai-conv-item");g&&g.dataset.name&&(this.loadConversationHistory(g.dataset.name),m&&m.classList.remove("open"))}),this.enableDragging()}startNewChat(){this.conversation=null,this.messages=[];let e=document.getElementById("erp-ai-messages");e&&(e.innerHTML="");let t=document.getElementById("erp-ai-welcome");t&&(t.style.display=""),document.querySelectorAll(".erp-ai-conv-item.active").forEach(a=>a.classList.remove("active"));let i=document.getElementById("erp-ai-sidebar");i&&i.classList.remove("open")}loadConversationsList(){let e=document.getElementById("erp-ai-conversations-list");!e||typeof frappe=="undefined"||frappe.call({method:"erp_ai.api.get_user_conversations",callback:t=>{let i=t.message&&t.message.status==="success"?t.message.data:[];if(!i||i.length===0){e.innerHTML='<div style="font-size: 12px; color: var(--erp-slate); text-align:center; padding-top:25px;">No conversations</div>';return}e.innerHTML="",i.forEach(a=>{let n=document.createElement("div");n.className="erp-ai-conv-item"+(a.name===this.conversation?" active":""),n.dataset.name=a.name,n.innerHTML=`
                        <span class="erp-ai-conv-title">${this.escapeHtml(a.title||a.name)}</span>
                        <button class="erp-ai-delete-conv" title="Delete chat">\u{1F5D1}\uFE0F</button>
                    `,e.appendChild(n)})}})}deleteConversation(e,t){typeof frappe!="undefined"&&(t.style.opacity="0.4",frappe.call({method:"erp_ai.api.delete_conversation",args:{conversation_name:e},callback:i=>{i.message&&i.message.status==="success"?(t.remove(),this.conversation===e&&this.startNewChat(),typeof frappe.show_alert=="function"&&frappe.show_alert({message:"Conversation deleted successfully",indicator:"green"})):t.style.opacity="1"},error:()=>{t.style.opacity="1"}}))}loadConversationHistory(e){typeof frappe!="undefined"&&frappe.call({method:"erp_ai.api.load_conversation",args:{conversation_name:e},callback:t=>{if(!t.message||t.message.status!=="success")return;this.conversation=t.message.name,this.messages=Array.isArray(t.message.messages)?t.message.messages:[];let i=document.getElementById("erp-ai-messages");i&&(i.innerHTML="");let a=document.getElementById("erp-ai-welcome");a&&(a.style.display="none"),this.messages.forEach(n=>this.addMessage(n.content,n.role==="user"?"user":"assistant",!1)),this.loadConversationsList()}})}enableDragging(){let e=document.getElementById("erp-ai-window"),t=document.getElementById("erp-ai-header");!e||!t||(e.addEventListener("dragstart",i=>i.preventDefault(),!0),t.addEventListener("dragstart",i=>i.preventDefault(),!0),t.addEventListener("mousedown",i=>{if(i.target.tagName==="BUTTON"||i.target.closest("button"))return;i.preventDefault(),this.dragging=!0;let a=e.getBoundingClientRect();e.style.left=a.left+"px",e.style.top=a.top+"px",e.style.right="auto",e.style.bottom="auto",this.dragOffsetX=i.clientX-a.left,this.dragOffsetY=i.clientY-a.top,document.body.style.userSelect="none"}),document.addEventListener("mousemove",i=>{!this.dragging||(e.style.left=i.clientX-this.dragOffsetX+"px",e.style.top=i.clientY-this.dragOffsetY+"px")}),document.addEventListener("mouseup",()=>{this.dragging&&(this.dragging=!1,document.body.style.userSelect="")}))}showWindow(){let e=document.getElementById("erp-ai-window");e&&(e.style.display="flex")}hideWindow(){let e=document.getElementById("erp-ai-window");e&&(e.style.display="none")}toggleWindow(){let e=document.getElementById("erp-ai-window");e&&(e.style.display==="flex"?this.hideWindow():this.showWindow())}scrollToBottom(){let e=document.getElementById("erp-ai-body");e&&(e.scrollTop=e.scrollHeight)}async sendMessage(e=null){let t=document.getElementById("erp-ai-input"),i=e!==null?e:t?t.value.trim():"";if(!i&&!this.attachedFileContent)return;t&&e===null&&(t.value="",t.style.height="auto");let a=document.getElementById("erp-ai-welcome");a&&(a.style.display="none");let n=i;this.attachedFileName&&(n+=`
[\u0645\u0631\u0641\u0642: ${this.attachedFileName}]`),this.messages.push({role:"user",content:i}),this.addMessage(n,"user",!1);let o={message:i||"\u0642\u0645 \u0628\u062A\u062D\u0644\u064A\u0644 \u0647\u0630\u0627 \u0627\u0644\u0645\u0644\u0641 \u0627\u0644\u0645\u0631\u0641\u0642",conversation:JSON.stringify(this.messages.slice(0,-1)),conversation_name:this.conversation};this.attachedFileContent&&(o.file_data=this.attachedFileContent,o.file_name=this.attachedFileName),this.attachedFileContent=null,this.attachedFileName="";let s=document.getElementById("erp-ai-file-preview");s&&(s.style.display="none"),this.showTyping();try{if(typeof frappe=="undefined")throw new Error("Frappe framework not detected.");let r=await frappe.call({method:"erp_ai.api.ask",args:o});if(this.hideTyping(),r&&r.message&&r.message.reply){r.message.conversation_name&&(this.conversation=r.message.conversation_name);let d=r.message.reply;Array.isArray(d)&&(d=d.join("")),this.addMessage(d,"assistant",!0),this.messages.push({role:"assistant",content:d});let l=document.getElementById("erp-ai-sidebar");l&&l.classList.contains("open")&&this.loadConversationsList()}else this.addMessage("No response received from AI.","assistant",!1)}catch(r){console.error(r),this.hideTyping(),this.addMessage("Something went wrong.","assistant",!1)}}extractTableData(e){try{let t=e.split(`
`).filter(s=>s.trim().includes("|")),i=t.findIndex(s=>s.match(/\|[-\s:]+\|/));if(i<1)return null;let a=s=>{let r=s.trim();return r.startsWith("|")&&(r=r.substring(1)),r.endsWith("|")&&(r=r.substring(0,r.length-1)),r.split("|").map(d=>d.trim())},n=a(t[i-1]),o=[];for(let s=i+1;s<t.length&&t[s].trim().includes("|");s++){let r=a(t[s]),d={};n.forEach((l,h)=>{d[l]=r[h]!==void 0?r[h]:""}),o.push(d)}return o.length>0?o:null}catch(t){return null}}escapeHtml(e){let t=document.createElement("div");return t.textContent=e==null?"":String(e),t.innerHTML}renderContent(e,t,i,a){let n=this.extractTableData(t);if(n&&n.length>0){let o=t.split(/\|.*\|/),s=o[0]?o[0].trim():"",r=`<div class="erp-text-content" style="margin-bottom: 10px;">${window.frappe&&frappe.markdown?frappe.markdown(s):this.escapeHtml(s)}</div>`;r+='<div style="overflow-x:auto; margin: 10px 0; border-radius: 8px; border: 1px solid var(--erp-border);"><table style="width:100%; border-collapse:collapse; font-size:12px; background:var(--erp-surface);"><tr style="background:var(--erp-surface-soft);">';let d=Object.keys(n[0]);d.forEach(m=>{r+=`<th style="padding:8px 10px; border-bottom:1px solid var(--erp-border); text-align:left; color:var(--erp-ink);">${this.escapeHtml(m)}</th>`}),r+="</tr>",n.forEach(m=>{r+="<tr>",d.forEach(x=>{r+=`<td style="padding:8px 10px; border-bottom:1px solid var(--erp-border); color:var(--erp-ink);">${this.escapeHtml(m[x]||"")}</td>`}),r+="</tr>"}),r+="</table></div>",r+=`<button type="button" class="export-csv-btn" data-csv-payload="${encodeURIComponent(JSON.stringify(n))}" style="cursor:pointer; background:var(--erp-surface-soft); border:1px solid var(--erp-border); color:var(--erp-ink); border-radius:8px; padding:8px; font-size:12px; font-weight:600; width:100%; margin-top:8px; transition: background 150ms;">\u2B07 Download (CSV)</button>`,e.innerHTML=r;let h=e.querySelector(".export-csv-btn");h&&h.addEventListener("click",()=>{try{let m=JSON.parse(decodeURIComponent(h.dataset.csvPayload));this.downloadFallbackCSV(m)}catch(m){console.error(m)}}),a&&a()}else if(i){e.classList.add("erp-typing-cursor");let o=0,s=12,r=t.length,d=setInterval(()=>{if(o<r){let l=t.substring(0,o+1);e.innerHTML=window.frappe&&frappe.markdown?frappe.markdown(l):this.escapeHtml(l),o++,this.scrollToBottom()}else clearInterval(d),e.classList.remove("erp-typing-cursor"),e.innerHTML=window.frappe&&frappe.markdown?frappe.markdown(t):this.escapeHtml(t),a&&a()},s)}else e.innerHTML=window.frappe&&frappe.markdown?frappe.markdown(t):this.escapeHtml(t),a&&a()}addMessage(e,t,i=!1){let a=document.getElementById("erp-ai-messages");if(!a)return;let n=document.createElement("div");n.className="erp-ai-row "+t;let o=document.createElement("div");o.className="erp-ai-avatar",o.textContent=t==="user"?"\u{1F464}":"AI";let s=document.createElement("div");s.className="erp-ai-message-container";let r=document.createElement("div");r.className="erp-ai-message "+t;let d=String(e).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g,"").trim();if(t==="assistant"){let l=document.createElement("div");l.className="erp-ai-msg-actions",l.innerHTML=`
                <button class="erp-ai-action-btn erp-copy-btn" title="Copy text">\u{1F4CB} Copy</button>
                <button class="erp-ai-action-btn erp-regen-btn" title="Regenerate response">\u{1F504} Regenerate</button>
            `,l.querySelector(".erp-copy-btn").addEventListener("click",()=>{navigator.clipboard.writeText(d).then(()=>{typeof frappe!="undefined"&&typeof frappe.show_alert=="function"?frappe.show_alert({message:"Copied to clipboard",indicator:"green"}):alert("Copied to clipboard")}).catch(h=>{console.error("Failed to copy text: ",h)})}),l.querySelector(".erp-regen-btn").addEventListener("click",()=>{if(this.messages.length>=2){this.messages.pop();let h=this.messages.pop();h&&(n.remove(),this.sendMessage(h.content))}}),this.renderContent(r,d,i,()=>{this.scrollToBottom()}),s.appendChild(r),s.appendChild(l)}else r.textContent=d,s.appendChild(r);n.appendChild(o),n.appendChild(s),a.appendChild(n),this.scrollToBottom()}downloadFallbackCSV(e){if(!e||!e.length)return;let t=Object.keys(e[0]),i=t.join(",")+`
`;e.forEach(o=>{i+=t.map(s=>`"${(o[s]||"").toString().replace(/"/g,'""')}"`).join(",")+`
`});let a=new Blob(["\uFEFF"+i],{type:"text/css;charset=utf-8;"}),n=document.createElement("a");n.href=URL.createObjectURL(a),n.download=`report_${Date.now()}.csv`,n.click()}showTyping(){if(this.typing)return;this.typing=!0;let e=document.getElementById("erp-ai-messages");if(!e)return;let t=document.createElement("div");t.className="erp-ai-row assistant erp-ai-typing-row",t.innerHTML=`
            <div class="erp-ai-avatar">AI</div>
            <div class="erp-ai-message-container">
                <div class="erp-ai-loading-dots"><span></span><span></span><span></span></div>
            </div>
        `,e.append(t),this.scrollToBottom()}hideTyping(){this.typing,this.typing=!1;let e=document.querySelector(".erp-ai-typing-row");e&&e.remove()}};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>new b):new b;})();
//# sourceMappingURL=erp_ai.bundle.CCRBB733.js.map
