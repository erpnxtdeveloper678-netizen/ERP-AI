(()=>{var h=class{constructor(){if(window.__erpAiInstance)return console.warn("ERP AI: an instance is already running on this page \u2014 skipping duplicate initialization. If you keep seeing this, check for erp_ai.js being registered/loaded from more than one place (hooks.py, a Client Script, or a stale cached bundle)."),window.__erpAiInstance;window.__erpAiInstance=this,document.querySelectorAll("#erp-ai-window, #erp-ai-button").forEach(e=>e.remove()),this.messages=[],this.conversation=null,this.typing=!1,this.dragging=!1,this.dragOffsetX=0,this.dragOffsetY=0,this.attachedFileContent=null,this.attachedFileName="",this.resizing=!1,this.resizeStartX=0,this.resizeStartY=0,this.resizeStartWidth=0,this.resizeStartHeight=0,this.minWidth=320,this.minHeight=420,this.injectStyles(),this.createButton(),this.createWindow()}injectStyles(){if(document.getElementById("erp-ai-styles"))return;let e=document.createElement("style");e.id="erp-ai-styles",e.textContent=`
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
        `,document.head.appendChild(e)}async loadTemplate(){let e=await fetch("/assets/erp_ai/chat.html");if(!e.ok)throw new Error("Failed to load ERP AI template.");return await e.text()}createButton(){if(document.getElementById("erp-ai-button"))return;let e=document.createElement("div");e.id="erp-ai-button",e.innerHTML=`
            <div class="button-logo-inside" style="display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; font-weight: bold; font-family: inherit;">
                <span style="color: #2563eb; font-size: 15px;">E</span><span style="color: #0f172a; font-size: 15px;">AI</span>
            </div>
        `,document.body.appendChild(e),e.addEventListener("click",()=>this.toggleWindow())}async createWindow(){if(document.getElementById("erp-ai-window"))return;let e=document.createElement("div");e.id="erp-ai-window",e.style.display="none",document.body.appendChild(e);try{let t=await this.loadTemplate();if(document.querySelectorAll("#erp-ai-window").length>1){e.remove();return}e.innerHTML=t,this.setupResizableWindow(),this.bindEvents()}catch(t){console.error(t),e.innerHTML='<div style="padding:20px; color:red; font-weight:bold;">Failed to load ERP AI UI.</div>'}}setupResizableWindow(){let e=document.getElementById("erp-ai-window");if(!e)return;let t=window.getComputedStyle(e),n=t.position;if(n!=="fixed"&&n!=="absolute"&&(e.style.position="fixed"),e.style.zIndex||(e.style.zIndex="9999"),[t.top,t.left,t.right,t.bottom].some(a=>a&&a!=="auto")||(e.style.right="24px",e.style.bottom="90px"),e.style.minWidth=this.minWidth+"px",e.style.minHeight=this.minHeight+"px",e.style.maxWidth="95vw",e.style.maxHeight="90vh",e.style.boxSizing="border-box",!document.getElementById("erp-ai-resize-handle")){let a=document.createElement("div");a.id="erp-ai-resize-handle",a.title="Drag to resize",a.style.cssText=`
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
            `,e.appendChild(a),a.addEventListener("mousedown",o=>{o.preventDefault(),o.stopPropagation(),this.resizing=!0;let r=e.getBoundingClientRect();this.resizeStartX=o.clientX,this.resizeStartY=o.clientY,this.resizeStartWidth=r.width,this.resizeStartHeight=r.height,document.body.style.userSelect="none"})}document.addEventListener("mousemove",a=>{if(!this.resizing)return;let o=a.clientX-this.resizeStartX,r=a.clientY-this.resizeStartY,i=this.resizeStartWidth+o,d=this.resizeStartHeight+r,c=window.innerWidth*.95,l=window.innerHeight*.9;i=Math.min(Math.max(i,this.minWidth),c),d=Math.min(Math.max(d,this.minHeight),l),e.style.width=i+"px",e.style.height=d+"px"}),document.addEventListener("mouseup",()=>{this.resizing&&(this.resizing=!1,document.body.style.userSelect="")}),window.addEventListener("resize",()=>{let a=e.getBoundingClientRect(),o=window.innerWidth*.95,r=window.innerHeight*.9;a.width>o&&(e.style.width=o+"px"),a.height>r&&(e.style.height=r+"px");let i=e.getBoundingClientRect();i.right>window.innerWidth&&(e.style.left=Math.max(0,window.innerWidth-i.width)+"px"),i.bottom>window.innerHeight&&(e.style.top=Math.max(0,window.innerHeight-i.height)+"px")})}bindEvents(){let e=document.getElementById("erp-ai-input");document.getElementById("erp-ai-close").addEventListener("click",()=>this.hideWindow()),document.getElementById("erp-ai-minimize").addEventListener("click",()=>this.hideWindow()),document.getElementById("erp-ai-send").addEventListener("click",()=>this.sendMessage()),e.addEventListener("keydown",i=>{i.key==="Enter"&&!i.shiftKey&&(i.preventDefault(),this.sendMessage())}),e.addEventListener("input",function(){this.style.height="auto",this.style.height=this.scrollHeight+"px"});let t=document.getElementById("erp-ai-file-input");document.getElementById("erp-ai-attach-btn")&&t&&t.addEventListener("change",i=>{let d=i.target.files[0];if(!d)return;this.attachedFileName=d.name;let c=new FileReader;c.onload=l=>{this.attachedFileContent=l.target.result;let m=document.getElementById("erp-ai-file-preview");m&&(m.style.display="inline-block",m.innerText=`\u{1F4CE} ${this.attachedFileName}`)},c.readAsText(d)}),document.querySelectorAll(".erp-ai-suggestion").forEach(i=>{i.addEventListener("click",()=>{e.value=i.dataset.message,e.dispatchEvent(new Event("input")),e.focus()})});let s=document.getElementById("erp-ai-toggle-sidebar"),a=document.getElementById("erp-ai-sidebar");s&&a&&s.addEventListener("click",()=>{let i=a.classList.toggle("open");s.classList.toggle("active",i),i&&this.loadConversationsList()});let o=document.getElementById("erp-ai-new-chat");o&&o.addEventListener("click",()=>this.startNewChat());let r=document.getElementById("erp-ai-conversations-list");r&&r.addEventListener("click",i=>{let d=i.target.closest(".erp-ai-conv-item");d&&d.dataset.name&&this.loadConversationHistory(d.dataset.name)}),this.enableDragging()}startNewChat(){this.conversation=null,this.messages=[];let e=document.getElementById("erp-ai-messages");e&&(e.innerHTML="");let t=document.getElementById("erp-ai-welcome");t&&(t.style.display=""),document.querySelectorAll(".erp-ai-conv-item.active").forEach(n=>n.classList.remove("active")),this.focusInput()}loadConversationsList(){let e=document.getElementById("erp-ai-conversations-list");!e||frappe.call({method:"erp_ai.api.get_user_conversations",callback:t=>{let n=t.message&&t.message.status==="success"?t.message.data:[];if(!n||n.length===0){e.innerHTML='<div class="erp-ai-sidebar-empty">No conversations yet</div>';return}e.innerHTML="",n.forEach(s=>{let a=document.createElement("div");a.className="erp-ai-conv-item"+(s.name===this.conversation?" active":""),a.dataset.name=s.name,a.title=s.title||s.name,a.textContent=s.title||s.name,e.appendChild(a)})},error:()=>{e.innerHTML='<div class="erp-ai-sidebar-empty">Could not load conversations</div>'}})}loadConversationHistory(e){frappe.call({method:"erp_ai.api.load_conversation",args:{conversation_name:e},callback:t=>{if(!t.message||t.message.status!=="success"){console.error("ERP AI: failed to load conversation",t.message);return}this.conversation=t.message.name,this.messages=Array.isArray(t.message.messages)?t.message.messages:[];let n=document.getElementById("erp-ai-messages");n&&(n.innerHTML="");let s=document.getElementById("erp-ai-welcome");s&&(s.style.display="none"),this.messages.forEach(a=>{this.addMessage(a.content,a.role==="user"?"user":"assistant")}),document.querySelectorAll(".erp-ai-conv-item").forEach(a=>{a.classList.toggle("active",a.dataset.name===e)}),this.scrollToBottom()}})}enableDragging(){let e=document.getElementById("erp-ai-window"),t=document.getElementById("erp-ai-header");if(!e||!t){console.warn('ERP AI: dragging not enabled \u2014 could not find #erp-ai-window and/or #erp-ai-header in the DOM. Make sure the header bar element in chat.html has id="erp-ai-header".');return}t.addEventListener("dragstart",n=>n.preventDefault()),t.addEventListener("mousedown",n=>{if(n.target.tagName==="BUTTON"||n.target.closest("button"))return;this.dragging=!0;let s=e.getBoundingClientRect();e.style.left=s.left+"px",e.style.top=s.top+"px",e.style.right="auto",e.style.bottom="auto",this.dragOffsetX=n.clientX-s.left,this.dragOffsetY=n.clientY-s.top,document.body.style.userSelect="none"}),document.addEventListener("mousemove",n=>{!this.dragging||(e.style.left=n.clientX-this.dragOffsetX+"px",e.style.top=n.clientY-this.dragOffsetY+"px")}),document.addEventListener("mouseup",()=>{this.dragging&&(this.dragging=!1,document.body.style.userSelect="")})}showWindow(){document.getElementById("erp-ai-window").style.display="flex",this.focusInput()}hideWindow(){document.getElementById("erp-ai-window").style.display="none"}toggleWindow(){document.getElementById("erp-ai-window").style.display==="flex"?this.hideWindow():this.showWindow()}focusInput(){let e=document.getElementById("erp-ai-input");e&&e.focus()}async sendMessage(){let e=document.getElementById("erp-ai-input"),t=e.value.trim();if(!t&&!this.attachedFileContent)return;e.value="",e.style.height="auto";let n=document.getElementById("erp-ai-welcome");n&&(n.style.display="none");let s=t;this.attachedFileName&&(s+=`
[\u0645\u0631\u0641\u0642: ${this.attachedFileName}]`),this.messages.push({role:"user",content:t}),this.addMessage(s,"user");let a={message:t,conversation:JSON.stringify(this.messages.slice(0,-1)),conversation_name:this.conversation};this.attachedFileContent&&(a.file_data=this.attachedFileContent,a.file_name=this.attachedFileName),this.attachedFileContent=null,this.attachedFileName="";let o=document.getElementById("erp-ai-file-preview");o&&(o.style.display="none");let r=document.getElementById("erp-ai-file-input");r&&(r.value=""),this.showTyping();try{let i=await frappe.call({method:"erp_ai.api.ask",args:a});if(this.hideTyping(),i&&i.message&&i.message.reply){if(i.message.conversation_name){let c=this.conversation!==i.message.conversation_name;this.conversation=i.message.conversation_name;let l=document.getElementById("erp-ai-sidebar");c&&l&&l.classList.contains("open")&&this.loadConversationsList()}let d=i.message.reply;Array.isArray(d)&&(d=d.join("")),this.addMessage(d,"assistant"),this.messages.push({role:"assistant",content:d})}else this.addMessage("No response received from AI.","assistant")}catch(i){console.error(i),this.hideTyping(),this.addMessage("Something went wrong.","assistant")}}extractTableData(e){try{let t=e.split(`
`).filter(r=>r.trim().includes("|")),n=t.findIndex(r=>r.match(/\|[-\s:]+\|/));if(n<1)return null;let s=r=>{let i=r.trim();return i.startsWith("|")&&(i=i.substring(1)),i.endsWith("|")&&(i=i.substring(0,i.length-1)),i.split("|").map(d=>d.trim())},a=s(t[n-1]),o=[];for(let r=n+1;r<t.length&&t[r].trim().includes("|");r++){let i=s(t[r]),d={};a.forEach((c,l)=>{d[c]=i[l]!==void 0?i[l]:""}),o.push(d)}return o.length>0?o:null}catch(t){return console.error("Error parsing table:",t),null}}escapeHtml(e){let t=document.createElement("div");return t.textContent=e==null?"":String(e),t.innerHTML}addMessage(e,t){let n=document.getElementById("erp-ai-messages"),s=document.createElement("div");s.className="erp-ai-row "+t;let a=document.createElement("div");a.className="erp-ai-avatar",a.innerHTML=t==="user"?"\u{1F464}":'<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';let o=document.createElement("div");o.className="erp-ai-message "+t;let r=typeof e=="object"?e.reply||JSON.stringify(e):e;if(r=String(r).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g,"").trim(),t==="assistant"){let i=this.extractTableData(String(r));if(i&&i.length>0){let d=String(r).split(/\|.*\|/),c=d[0]?d[0].trim():"",l=`<div class="ai-text-part" style="margin-bottom: 10px;">${window.frappe&&frappe.markdown?frappe.markdown(c):this.escapeHtml(c)}</div>`;l+=`<div class="table-responsive" style="margin-top: 8px; margin-bottom: 8px; overflow-x: auto;">
                    <table class="table table-bordered table-striped" style="width: 100%; background: #fff; font-size: 11px; color: #333; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f1f3f5;">`;let m=Object.keys(i[0]);m.forEach(p=>{l+=`<th style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(p)}</th>`}),l+="</tr></thead><tbody>",i.forEach((p,u)=>{l+=`<tr style="animation-delay: ${Math.min(u*55,500)}ms;">`,m.forEach(f=>{l+=`<td style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(p[f]||"")}</td>`}),l+="</tr>"}),l+="</tbody></table></div>",l+=`
                    <div class="message-actions" style="margin-top: 10px; clear: both; width: 100%;">
                        <button type="button" class="btn btn-xs btn-default export-csv-btn" data-csv-payload="${encodeURIComponent(JSON.stringify(i))}" style="cursor: pointer; background: #f8f9fa; border: 1px solid #cbd5d1; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: #2c3e50; width: 100%; box-sizing: border-box;">
                            <i class="fa fa-download"></i> Download (CSV)
                        </button>
                    </div>
                `,o.innerHTML=l;let g=o.querySelector(".export-csv-btn");g&&g.addEventListener("click",()=>{try{let p=JSON.parse(decodeURIComponent(g.dataset.csvPayload));window.downloadReportCSV(p)}catch(p){console.error("Failed to parse CSV payload:",p)}})}else o.innerHTML=window.frappe&&frappe.markdown?frappe.markdown(String(r)):this.escapeHtml(r)}else o.textContent=r;s.appendChild(a),s.appendChild(o),n.appendChild(s),this.scrollToBottom()}showTyping(){if(this.typing)return;this.typing=!0;let e=document.getElementById("erp-ai-messages"),t=document.createElement("div");t.className="erp-ai-row assistant erp-ai-typing-row";let n=document.createElement("div");n.className="erp-ai-avatar erp-ai-thinking",n.innerHTML='<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';let s=document.createElement("div");s.className="erp-ai-message assistant",s.innerHTML=`
            <div class="erp-ai-loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `,t.appendChild(n),t.appendChild(s),e.appendChild(t),this.scrollToBottom()}hideTyping(){this.typing=!1;let e=document.querySelector(".erp-ai-typing-row");e&&e.remove()}scrollToBottom(){let e=document.getElementById("erp-ai-body");e&&(e.scrollTop=e.scrollHeight)}};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>{new h}):new h;})();
//# sourceMappingURL=erp_ai.bundle.NOVJJWZT.js.map
