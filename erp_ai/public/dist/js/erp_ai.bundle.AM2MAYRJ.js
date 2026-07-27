(()=>{var g=class{constructor(){if(window.__erpAiInstance)return console.warn("ERP AI: an instance is already running on this page \u2014 skipping duplicate initialization. If you keep seeing this, check for erp_ai.js being registered/loaded from more than one place (hooks.py, a Client Script, or a stale cached bundle)."),window.__erpAiInstance;window.__erpAiInstance=this,document.querySelectorAll("#erp-ai-window, #erp-ai-button").forEach(e=>e.remove()),this.messages=[],this.conversation=null,this.typing=!1,this.dragging=!1,this.dragOffsetX=0,this.dragOffsetY=0,this.attachedFileContent=null,this.attachedFileName="",this.resizing=!1,this.resizeStartX=0,this.resizeStartY=0,this.resizeStartWidth=0,this.resizeStartHeight=0,this.minWidth=320,this.minHeight=420,this.injectStyles(),this.createButton(),this.createWindow()}injectStyles(){if(document.getElementById("erp-ai-styles"))return;let e=document.createElement("style");e.id="erp-ai-styles",e.textContent=`
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
        `,document.body.appendChild(e),e.addEventListener("click",()=>this.toggleWindow())}async createWindow(){if(document.getElementById("erp-ai-window"))return;let e=document.createElement("div");e.id="erp-ai-window",e.style.display="none",document.body.appendChild(e);try{let t=await this.loadTemplate();if(document.querySelectorAll("#erp-ai-window").length>1){e.remove();return}e.innerHTML=t,this.setupResizableWindow(),this.bindEvents()}catch(t){console.error(t),e.innerHTML='<div style="padding:20px; color:red; font-weight:bold;">Failed to load ERP AI UI.</div>'}}setupResizableWindow(){let e=document.getElementById("erp-ai-window");if(!e)return;let t=window.getComputedStyle(e),o=t.position;if(o!=="fixed"&&o!=="absolute"&&(e.style.position="fixed"),e.style.zIndex||(e.style.zIndex="9999"),[t.top,t.left,t.right,t.bottom].some(n=>n&&n!=="auto")||(e.style.right="24px",e.style.bottom="90px"),e.style.minWidth=this.minWidth+"px",e.style.minHeight=this.minHeight+"px",e.style.maxWidth="95vw",e.style.maxHeight="90vh",e.style.boxSizing="border-box",!document.getElementById("erp-ai-resize-handle")){let n=document.createElement("div");n.id="erp-ai-resize-handle",n.title="Drag to resize",n.style.cssText=`
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
            `,e.appendChild(n),n.addEventListener("mousedown",r=>{r.preventDefault(),r.stopPropagation(),this.resizing=!0;let s=e.getBoundingClientRect();this.resizeStartX=r.clientX,this.resizeStartY=r.clientY,this.resizeStartWidth=s.width,this.resizeStartHeight=s.height,document.body.style.userSelect="none"})}document.addEventListener("mousemove",n=>{if(!this.resizing)return;let r=n.clientX-this.resizeStartX,s=n.clientY-this.resizeStartY,i=this.resizeStartWidth+r,d=this.resizeStartHeight+s,c=window.innerWidth*.95,l=window.innerHeight*.9;i=Math.min(Math.max(i,this.minWidth),c),d=Math.min(Math.max(d,this.minHeight),l),e.style.width=i+"px",e.style.height=d+"px"}),document.addEventListener("mouseup",()=>{this.resizing&&(this.resizing=!1,document.body.style.userSelect="")}),window.addEventListener("resize",()=>{let n=e.getBoundingClientRect(),r=window.innerWidth*.95,s=window.innerHeight*.9;n.width>r&&(e.style.width=r+"px"),n.height>s&&(e.style.height=s+"px");let i=e.getBoundingClientRect();i.right>window.innerWidth&&(e.style.left=Math.max(0,window.innerWidth-i.width)+"px"),i.bottom>window.innerHeight&&(e.style.top=Math.max(0,window.innerHeight-i.height)+"px")})}bindEvents(){let e=document.getElementById("erp-ai-input");document.getElementById("erp-ai-close").addEventListener("click",()=>this.hideWindow()),document.getElementById("erp-ai-minimize").addEventListener("click",()=>this.hideWindow()),document.getElementById("erp-ai-send").addEventListener("click",()=>this.sendMessage()),e.addEventListener("keydown",a=>{a.key==="Enter"&&!a.shiftKey&&(a.preventDefault(),this.sendMessage())}),e.addEventListener("input",function(){this.style.height="auto",this.style.height=this.scrollHeight+"px"});let t=document.getElementById("erp-ai-file-input");document.getElementById("erp-ai-attach-btn")&&t&&t.addEventListener("change",a=>{let n=a.target.files[0];if(!n)return;this.attachedFileName=n.name;let r=new FileReader;r.onload=s=>{this.attachedFileContent=s.target.result;let i=document.getElementById("erp-ai-file-preview");i&&(i.style.display="inline-block",i.innerText=`\u{1F4CE} ${this.attachedFileName}`)},r.readAsText(n)}),document.querySelectorAll(".erp-ai-suggestion").forEach(a=>{a.addEventListener("click",()=>{e.value=a.dataset.message,e.dispatchEvent(new Event("input")),e.focus()})}),this.enableDragging()}enableDragging(){let e=document.getElementById("erp-ai-window"),t=document.getElementById("erp-ai-header");if(!e||!t){console.warn('ERP AI: dragging not enabled \u2014 could not find #erp-ai-window and/or #erp-ai-header in the DOM. Make sure the header bar element in chat.html has id="erp-ai-header".');return}t.addEventListener("dragstart",o=>o.preventDefault()),t.addEventListener("mousedown",o=>{if(o.target.tagName==="BUTTON"||o.target.closest("button"))return;this.dragging=!0;let a=e.getBoundingClientRect();e.style.left=a.left+"px",e.style.top=a.top+"px",e.style.right="auto",e.style.bottom="auto",this.dragOffsetX=o.clientX-a.left,this.dragOffsetY=o.clientY-a.top,document.body.style.userSelect="none"}),document.addEventListener("mousemove",o=>{!this.dragging||(e.style.left=o.clientX-this.dragOffsetX+"px",e.style.top=o.clientY-this.dragOffsetY+"px")}),document.addEventListener("mouseup",()=>{this.dragging&&(this.dragging=!1,document.body.style.userSelect="")})}showWindow(){document.getElementById("erp-ai-window").style.display="flex",this.focusInput()}hideWindow(){document.getElementById("erp-ai-window").style.display="none"}toggleWindow(){document.getElementById("erp-ai-window").style.display==="flex"?this.hideWindow():this.showWindow()}focusInput(){let e=document.getElementById("erp-ai-input");e&&e.focus()}async sendMessage(){let e=document.getElementById("erp-ai-input"),t=e.value.trim();if(!t&&!this.attachedFileContent)return;e.value="",e.style.height="auto";let o=document.getElementById("erp-ai-welcome");o&&(o.style.display="none");let a=t;this.attachedFileName&&(a+=`
[\u0645\u0631\u0641\u0642: ${this.attachedFileName}]`),this.messages.push({role:"user",content:t}),this.addMessage(a,"user");let n={message:t,conversation:JSON.stringify(this.messages.slice(0,-1))};this.attachedFileContent&&(n.file_data=this.attachedFileContent,n.file_name=this.attachedFileName),this.attachedFileContent=null,this.attachedFileName="";let r=document.getElementById("erp-ai-file-preview");r&&(r.style.display="none");let s=document.getElementById("erp-ai-file-input");s&&(s.value=""),this.showTyping();try{let i=await frappe.call({method:"erp_ai.api.ask",args:n});if(this.hideTyping(),i&&i.message&&i.message.reply){let d=i.message.reply;Array.isArray(d)&&(d=d.join("")),this.addMessage(d,"assistant"),this.messages.push({role:"assistant",content:d})}else this.addMessage("No response received from AI.","assistant")}catch(i){console.error(i),this.hideTyping(),this.addMessage("Something went wrong.","assistant")}}extractTableData(e){try{let t=e.split(`
`).filter(s=>s.trim().includes("|")),o=t.findIndex(s=>s.match(/\|[-\s:]+\|/));if(o<1)return null;let a=s=>{let i=s.trim();return i.startsWith("|")&&(i=i.substring(1)),i.endsWith("|")&&(i=i.substring(0,i.length-1)),i.split("|").map(d=>d.trim())},n=a(t[o-1]),r=[];for(let s=o+1;s<t.length&&t[s].trim().includes("|");s++){let i=a(t[s]),d={};n.forEach((c,l)=>{d[c]=i[l]!==void 0?i[l]:""}),r.push(d)}return r.length>0?r:null}catch(t){return console.error("Error parsing table:",t),null}}escapeHtml(e){let t=document.createElement("div");return t.textContent=e==null?"":String(e),t.innerHTML}addMessage(e,t){let o=document.getElementById("erp-ai-messages"),a=document.createElement("div");a.className="erp-ai-row "+t;let n=document.createElement("div");n.className="erp-ai-avatar",n.innerHTML=t==="user"?"\u{1F464}":'<div style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center;">AI</div>';let r=document.createElement("div");r.className="erp-ai-message "+t;let s=typeof e=="object"?e.reply||JSON.stringify(e):e;if(s=String(s).replace(/<!--ERP_AI_PENDING_REPORT:[\s\S]*?-->/g,"").trim(),t==="assistant"){let i=this.extractTableData(String(s));if(i&&i.length>0){let d=String(s).split(/\|.*\|/),c=d[0]?d[0].trim():"",l=`<div class="ai-text-part" style="margin-bottom: 10px;">${window.frappe&&frappe.markdown?frappe.markdown(c):this.escapeHtml(c)}</div>`;l+=`<div class="table-responsive" style="margin-top: 8px; margin-bottom: 8px; overflow-x: auto;">
                    <table class="table table-bordered table-striped" style="width: 100%; background: #fff; font-size: 11px; color: #333; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f1f3f5;">`;let u=Object.keys(i[0]);u.forEach(p=>{l+=`<th style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(p)}</th>`}),l+="</tr></thead><tbody>",i.forEach((p,f)=>{l+=`<tr style="animation-delay: ${Math.min(f*55,500)}ms;">`,u.forEach(y=>{l+=`<td style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${this.escapeHtml(p[y]||"")}</td>`}),l+="</tr>"}),l+="</tbody></table></div>",l+=`
                    <div class="message-actions" style="margin-top: 10px; clear: both; width: 100%;">
                        <button type="button" class="btn btn-xs btn-default export-csv-btn" data-csv-payload="${encodeURIComponent(JSON.stringify(i))}" style="cursor: pointer; background: #f8f9fa; border: 1px solid #cbd5d1; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: #2c3e50; width: 100%; box-sizing: border-box;">
                            <i class="fa fa-download"></i> Download (CSV)
                        </button>
                    </div>
                `,r.innerHTML=l;let m=r.querySelector(".export-csv-btn");m&&m.addEventListener("click",()=>{try{let p=JSON.parse(decodeURIComponent(m.dataset.csvPayload));window.downloadReportCSV(p)}catch(p){console.error("Failed to parse CSV payload:",p)}})}else window.frappe&&frappe.markdown?r.innerHTML=frappe.markdown(String(s)):r.innerText=String(s)}else r.innerText=String(s);t==="user"?(a.appendChild(r),a.appendChild(n)):(a.appendChild(n),a.appendChild(r)),o.appendChild(a),this.scrollToBottom()}showTyping(){if(document.getElementById("erp-ai-typing"))return;let e=document.getElementById("erp-ai-messages"),t=document.createElement("div");t.id="erp-ai-typing",t.className="erp-ai-row assistant",t.innerHTML=`
            <div class="erp-ai-avatar erp-ai-thinking" style="font-size: 11px; font-weight: bold; color: #2563eb; display: flex; align-items: center; justify-content: center;">AI</div>
            <div class="erp-ai-message assistant">
                <div class="erp-ai-loading-dots"><span></span><span></span><span></span></div>
            </div>
        `,e.appendChild(t),this.scrollToBottom()}hideTyping(){let e=document.getElementById("erp-ai-typing");e&&e.remove()}scrollToBottom(){let e=document.getElementById("erp-ai-body");e&&(e.scrollTop=e.scrollHeight)}};$(function(){console.log("ERP AI Clean & Stable Version Loaded."),new g});window.downloadReportCSV=function(h,e="erp_report.csv"){if(typeof h=="string")try{h=JSON.parse(h)}catch(t){console.error("Invalid JSON data");return}frappe.call({method:"erp_ai.api.export_data_to_csv",args:{data_json:h,filename:e},callback:function(t){if(t.message&&t.message.status==="success"){let o=new Blob([t.message.filedata],{type:"text/csv;charset=utf-8;"}),a=document.createElement("a"),n=URL.createObjectURL(o);a.setAttribute("href",n),a.setAttribute("download",t.message.file_name),document.body.appendChild(a),a.click(),document.body.removeChild(a),URL.revokeObjectURL(n)}else frappe.msgprint(__("\u062D\u062F\u062B \u062E\u0637\u0623 \u0623\u062B\u0646\u0627\u0621 \u062A\u0635\u062F\u064A\u0631 \u0627\u0644\u0645\u0644\u0641"))}})};})();
//# sourceMappingURL=erp_ai.bundle.AM2MAYRJ.js.map
