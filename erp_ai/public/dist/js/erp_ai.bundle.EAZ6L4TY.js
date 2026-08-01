(()=>{var g=class{constructor(){if(window.__erpAiInstance)return console.warn("ERP AI: an instance is already running on this page \u2014 skipping duplicate initialization. If you keep seeing this, check for erp_ai.js being registered/loaded from more than one place (hooks.py, a Client Script, or a stale cached bundle)."),window.__erpAiInstance;window.__erpAiInstance=this,this.cleanupDuplicates(),this.messages=[],this.conversation=null,this.typing=!1,this.dragging=!1,this.dragOffsetX=0,this.dragOffsetY=0,this.attachedFileContent=null,this.attachedFileName="",this.resizing=!1,this.resizeStartX=0,this.resizeStartY=0,this.resizeStartWidth=0,this.resizeStartHeight=0,this.minWidth=320,this.minHeight=420,this.isCreatingWindow=!1,this.injectStyles(),this.createButton(),this.createWindow()}cleanupDuplicates(){document.querySelectorAll("#erp-ai-window, #erp-ai-button").forEach(e=>e.remove())}injectStyles(){if(document.getElementById("erp-ai-styles"))return;let e=document.createElement("style");e.id="erp-ai-styles",e.textContent=`
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
                position: fixed;
                right: 24px;
                bottom: 24px;
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: var(--erp-surface);
                cursor: pointer;
                z-index: 9998;
                box-shadow: 0 8px 24px rgba(37, 99, 235, 0.28), 0 2px 6px rgba(15, 23, 42, 0.12);
                transition: transform 220ms var(--erp-ease), box-shadow 220ms var(--erp-ease);
            }
            #erp-ai-button:hover {
                transform: translateY(-2px) scale(1.04);
                box-shadow: 0 12px 28px rgba(37, 99, 235, 0.36), 0 3px 8px rgba(15, 23, 42, 0.14);
            }
            #erp-ai-button:active { transform: translateY(0) scale(0.98); }

            #erp-ai-window {
                position: fixed;
                right: 24px;
                bottom: 90px;
                width: 380px;
                height: 600px;
                border-radius: 18px;
                background: var(--erp-surface);
                box-shadow: 0 20px 48px rgba(15, 23, 42, 0.18), 0 4px 16px rgba(15, 23, 42, 0.08);
                border: 1px solid var(--erp-border);
                animation: erp-ai-window-in 260ms var(--erp-ease);
                z-index: 9999;
                overflow: hidden;
                display: flex;
                flex-direction: column;
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
        `,document.body.appendChild(e),e.addEventListener("click",()=>this.toggleWindow())}async createWindow(){if(!(document.getElementById("erp-ai-window")||this.isCreatingWindow)){this.isCreatingWindow=!0;try{let e=await this.loadTemplate();if(document.getElementById("erp-ai-window")){this.isCreatingWindow=!1;return}let t=document.createElement("div");t.id="erp-ai-window",t.style.display="none",t.innerHTML=e,document.body.appendChild(t),this.setupResizableWindow(),this.bindEvents()}catch(e){console.error("ERP AI: UI initialization error:",e)}finally{this.isCreatingWindow=!1}}}setupResizableWindow(){let e=document.getElementById("erp-ai-window");if(!!e){if(e.style.minWidth=this.minWidth+"px",e.style.minHeight=this.minHeight+"px",e.style.maxWidth="95vw",e.style.maxHeight="90vh",!document.getElementById("erp-ai-resize-handle")){let t=document.createElement("div");t.id="erp-ai-resize-handle",t.title="Drag to resize",t.style.cssText=`
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
            `,e.appendChild(t),t.addEventListener("mousedown",i=>{i.preventDefault(),i.stopPropagation(),this.resizing=!0;let n=e.getBoundingClientRect();this.resizeStartX=i.clientX,this.resizeStartY=i.clientY,this.resizeStartWidth=n.width,this.resizeStartHeight=n.height,document.body.style.userSelect="none"})}document.addEventListener("mousemove",t=>{if(!this.resizing)return;let i=t.clientX-this.resizeStartX,n=t.clientY-this.resizeStartY,a=this.resizeStartWidth+i,d=this.resizeStartHeight+n,o=window.innerWidth*.95,s=window.innerHeight*.9;a=Math.min(Math.max(a,this.minWidth),o),d=Math.min(Math.max(d,this.minHeight),s),e.style.width=a+"px",e.style.height=d+"px"}),document.addEventListener("mouseup",()=>{this.resizing&&(this.resizing=!1,document.body.style.userSelect="")}),window.addEventListener("resize",()=>{let t=e.getBoundingClientRect(),i=window.innerWidth*.95,n=window.innerHeight*.9;t.width>i&&(e.style.width=i+"px"),t.height>n&&(e.style.height=n+"px")})}}bindEvents(){let e=document.getElementById("erp-ai-input"),t=document.getElementById("erp-ai-close"),i=document.getElementById("erp-ai-minimize"),n=document.getElementById("erp-ai-send");t&&t.addEventListener("click",()=>this.hideWindow()),i&&i.addEventListener("click",()=>this.hideWindow()),n&&n.addEventListener("click",()=>this.sendMessage()),e&&(e.addEventListener("keydown",r=>{r.key==="Enter"&&!r.shiftKey&&(r.preventDefault(),this.sendMessage())}),e.addEventListener("input",function(){this.style.height="auto",this.style.height=Math.min(this.scrollHeight,120)+"px"}));let a=document.getElementById("erp-ai-file-input"),d=document.getElementById("erp-ai-attach-btn");d&&a&&(d.addEventListener("click",()=>a.click()),a.addEventListener("change",r=>{let p=r.target.files[0];if(!p)return;this.attachedFileName=p.name;let u=new FileReader;u.onload=h=>{this.attachedFileContent=h.target.result;let c=document.getElementById("erp-ai-file-preview");c&&(c.style.display="inline-block",c.innerText=`\u{1F4CE} ${this.attachedFileName}`)},u.readAsText(p)})),document.querySelectorAll(".erp-ai-suggestion").forEach(r=>{r.addEventListener("click",()=>{e&&(e.value=r.dataset.message||r.textContent.trim(),e.dispatchEvent(new Event("input")),e.focus())})});let o=document.getElementById("erp-ai-toggle-sidebar"),s=document.getElementById("erp-ai-sidebar");o&&s&&o.addEventListener("click",()=>{let r=s.classList.toggle("open");o.classList.toggle("active",r),r&&this.loadConversationsList()});let l=document.getElementById("erp-ai-new-chat");l&&l.addEventListener("click",()=>this.startNewChat());let m=document.getElementById("erp-ai-conversations-list");m&&m.addEventListener("click",r=>{let p=r.target.closest(".erp-ai-conv-item");p&&p.dataset.name&&this.loadConversationHistory(p.dataset.name)}),this.enableDragging()}startNewChat(){this.conversation=null,this.messages=[];let e=document.getElementById("erp-ai-messages");e&&(e.innerHTML="");let t=document.getElementById("erp-ai-welcome");t&&(t.style.display=""),document.querySelectorAll(".erp-ai-conv-item.active").forEach(i=>i.classList.remove("active")),this.focusInput()}loadConversationsList(){let e=document.getElementById("erp-ai-conversations-list");!e||typeof frappe=="undefined"||frappe.call({method:"erp_ai.api.get_user_conversations",callback:t=>{let i=t.message&&t.message.status==="success"?t.message.data:[];if(!i||i.length===0){e.innerHTML='<div class="erp-ai-sidebar-empty">No conversations yet</div>';return}e.innerHTML="",i.forEach(n=>{let a=document.createElement("div");a.className="erp-ai-conv-item"+(n.name===this.conversation?" active":""),a.dataset.name=n.name,a.title=n.title||n.name,a.textContent=n.title||n.name,e.appendChild(a)})},error:()=>{e.innerHTML='<div class="erp-ai-sidebar-empty">Could not load conversations</div>'}})}loadConversationHistory(e){typeof frappe!="undefined"&&frappe.call({method:"erp_ai.api.load_conversation",args:{conversation_name:e},callback:t=>{if(!t.message||t.message.status!=="success"){console.error("ERP AI: failed to load conversation",t.message);return}this.conversation=t.message.name,this.messages=Array.isArray(t.message.messages)?t.message.messages:[];let i=document.getElementById("erp-ai-messages");i&&(i.innerHTML="");let n=document.getElementById("erp-ai-welcome");n&&(n.style.display="none"),this.messages.forEach(a=>{this.addMessage(a.content,a.role==="user"?"user":"assistant")}),document.querySelectorAll(".erp-ai-conv-item").forEach(a=>{a.classList.toggle("active",a.dataset.name===e)}),this.scrollToBottom()}})}enableDragging(){let e=document.getElementById("erp-ai-window"),t=document.getElementById("erp-ai-header");!e||!t||(t.addEventListener("dragstart",i=>i.preventDefault()),t.addEventListener("mousedown",i=>{if(i.target.tagName==="BUTTON"||i.target.closest("button"))return;this.dragging=!0;let n=e.getBoundingClientRect();e.style.left=n.left+"px",e.style.top=n.top+"px",e.style.right="auto",e.style.bottom="auto",this.dragOffsetX=i.clientX-n.left,this.dragOffsetY=i.clientY-n.top,document.body.style.userSelect="none"}),document.addEventListener("mousemove",i=>{!this.dragging||(e.style.left=i.clientX-this.dragOffsetX+"px",e.style.top=i.clientY-this.dragOffsetY+"px")}),document.addEventListener("mouseup",()=>{this.dragging&&(this.dragging=!1,document.body.style.userSelect="")}))}showWindow(){let e=document.getElementById("erp-ai-window");e&&(e.style.display="flex"),this.focusInput()}hideWindow(){let e=document.getElementById("erp-ai-window");e&&(e.style.display="none")}toggleWindow(){let e=document.getElementById("erp-ai-window");e?e.style.display==="flex"?this.hideWindow():this.showWindow():this.createWindow().then(()=>this.showWindow())}focusInput(){let e=document.getElementById("erp-ai-input");e&&e.focus()}scrollToBottom(){let e=document.getElementById("erp-ai-body");e&&(e.scrollTop=e.scrollHeight)}async sendMessage(){let e=document.getElementById("erp-ai-input"),t=e?e.value.trim():"";if(!t&&!this.attachedFileContent)return;e&&(e.value="",e.style.height="auto");let i=document.getElementById("erp-ai-welcome");i&&(i.style.display="none");let n=t;this.attachedFileName&&(n+=`
[\u0645\u0631\u0641\u0642: ${this.attachedFileName}]`),this.messages.push({role:"user",content:t}),this.addMessage(n,"user");let a={message:t,conversation:JSON.stringify(this.messages.slice(0,-1)),conversation_name:this.conversation};this.attachedFileContent&&(a.file_data=this.attachedFileContent,a.file_name=this.attachedFileName),this.attachedFileContent=null,this.attachedFileName="";let d=document.getElementById("erp-ai-file-preview");d&&(d.style.display="none");let o=document.getElementById("erp-ai-file-input");o&&(o.value=""),this.showTyping();try{if(typeof frappe=="undefined")throw new Error("Frappe framework not detected.");let s=await frappe.call({method:"erp_ai.api.ask",args:a});if(this.hideTyping(),s&&s.message&&s.message.reply){if(s.message.conversation_name){let m=this.conversation!==s.message.conversation_name;this.conversation=s.message.conversation_name;let r=document.getElementById("erp-ai-sidebar");m&&r&&r.classList.contains("open")&&this.loadConversationsList()}let l=s.message.reply;Array.isArray(l)&&(l=l.join("")),this.addMessage(l,"assistant"),this.messages.push({role:"assistant",content:l})}else this.addMessage("No response received from AI.","assistant")}catch(s){console.error(s),this.hideTyping(),this.addMessage("Something went wrong.","assistant")}}extractTableData(e){try{let t=e.split(`
`).filter(o=>o.trim().includes("|")),i=t.findIndex(o=>o.match(/\|[-\s:]+\|/));if(i<1)return null;let n=o=>{let s=o.trim();return s.startsWith("|")&&(s=s.substring(1)),s.endsWith("|")&&(s=s.substring(0,s.length-1)),s.split("|").map(l=>l.trim())},a=n(t[i-1]),d=[];for(let o=i+1;o<t.length&&t[o].trim().includes("|");o++){let s=n(t[o]),l={};a.forEach((m,r)=>{l[m]=s[r]!==void 0?s[r]:""}),d.push(l)}return d.length>0?d:null}catch(t){return console.error("Error parsing table:",t),null}}escapeHtml(e){let t=document.createElement("div");return t.textContent=e==null?"":String(e),t.innerHTML}addMessage(e,t){let i=document.getElementById("erp-ai-messages");if(!i)return;let n=document.createElement("div");n.className="erp-ai-row "+t;let a=document.createElement("div");a.className="erp-ai-avatar",a.innerHTML=t==="user"?"\u{1F464}":'<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';let d=document.createElement("div");d.className="erp-ai-message "+t;let o=typeof e=="object"?e.reply||JSON.stringify(e):e;if(o=String(o).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g,"").trim(),t==="assistant"){let s=this.extractTableData(String(o));if(s&&s.length>0){let l=String(o).split(/\|.*\|/),m=l[0]?l[0].trim():"",r=`<div class="ai-text-part" style="margin-bottom: 10px;">${window.frappe&&frappe.markdown?frappe.markdown(m):this.escapeHtml(m)}</div>`;r+=`<div class="table-responsive" style="margin-top: 8px; margin-bottom: 8px; overflow-x: auto;">
                    <table class="table table-bordered table-striped" style="width: 100%; background: #fff; font-size: 11px; color: #333; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f1f3f5;">`;let p=Object.keys(s[0]);p.forEach(c=>{r+=`<th style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(c)}</th>`}),r+="</tr></thead><tbody>",s.forEach((c,f)=>{r+=`<tr style="animation-delay: ${Math.min(f*55,500)}ms;">`,p.forEach(y=>{r+=`<td style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(c[y]||"")}</td>`}),r+="</tr>"}),r+="</tbody></table></div>",r+=`
                    <div class="message-actions" style="margin-top: 10px; clear: both; width: 100%;">
                        <button type="button" class="btn btn-xs btn-default export-csv-btn" data-csv-payload="${encodeURIComponent(JSON.stringify(s))}" style="cursor: pointer; background: #f8f9fa; border: 1px solid #cbd5d1; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: #2c3e50; width: 100%; box-sizing: border-box;">
                            <i class="fa fa-download"></i> Download (CSV)
                        </button>
                    </div>
                `,d.innerHTML=r;let h=d.querySelector(".export-csv-btn");h&&h.addEventListener("click",()=>{try{let c=JSON.parse(decodeURIComponent(h.dataset.csvPayload));typeof window.downloadReportCSV=="function"?window.downloadReportCSV(c):this.downloadFallbackCSV(c)}catch(c){console.error("Failed to parse CSV payload:",c)}})}else d.innerHTML=window.frappe&&frappe.markdown?frappe.markdown(String(o)):this.escapeHtml(o)}else d.textContent=o;n.appendChild(a),n.appendChild(d),i.appendChild(n),this.scrollToBottom()}downloadFallbackCSV(e){if(!e||!e.length)return;let t=Object.keys(e[0]),i=t.join(",")+`
`;e.forEach(d=>{i+=t.map(o=>`"${(d[o]||"").toString().replace(/"/g,'""')}"`).join(",")+`
`});let n=new Blob(["\uFEFF"+i],{type:"text/csv;charset=utf-8;"}),a=document.createElement("a");a.href=URL.createObjectURL(n),a.download=`report_${Date.now()}.csv`,a.click()}showTyping(){if(this.typing)return;this.typing=!0;let e=document.getElementById("erp-ai-messages");if(!e)return;let t=document.createElement("div");t.className="erp-ai-row assistant erp-ai-typing-row";let i=document.createElement("div");i.className="erp-ai-avatar erp-ai-thinking",i.innerHTML='<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">AI</div>';let n=document.createElement("div");n.className="erp-ai-message assistant",n.innerHTML=`
            <div class="erp-ai-loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `,t.appendChild(i),t.appendChild(n),e.appendChild(t),this.scrollToBottom()}hideTyping(){this.typing=!1;let e=document.querySelector(".erp-ai-typing-row");e&&e.remove()}};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>new g):new g;})();
//# sourceMappingURL=erp_ai.bundle.EAZ6L4TY.js.map
