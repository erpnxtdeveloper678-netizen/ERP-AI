

class ERPAI {

    constructor() {
        this.messages = [];
        this.conversation = null;
        this.typing = false;
        this.dragging = false;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;
        this.createButton();
        this.createWindow();
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
        button.innerHTML = "🤖";
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
            windowElement.innerHTML = html;
            this.bindEvents();
        } catch (e) {
            console.error(e);
            windowElement.innerHTML = `<div style="padding:20px; color:red; font-weight:bold;">Failed to load ERP AI UI.</div>`;
        }
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

        document.querySelectorAll(".erp-ai-suggestion").forEach(button => {
            button.addEventListener("click", () => {
                input.value = button.dataset.message;
                input.dispatchEvent(new Event("input"));
                input.focus();
            });
        });
        this.enableDragging();
    }

    enableDragging() {
        const windowEl = document.getElementById("erp-ai-window");
        const header = document.getElementById("erp-ai-header");

        header.addEventListener("mousedown", (e) => {
            if (e.target.tagName === "BUTTON") return;
            this.dragging = true;
            const rect = windowEl.getBoundingClientRect();
            this.dragOffsetX = e.clientX - rect.left;
            this.dragOffsetY = e.clientY - rect.top;
            document.body.style.userSelect = "none";
        });

        document.addEventListener("mousemove", (e) => {
            if (!this.dragging) return;
            windowEl.style.left = (e.clientX - this.dragOffsetX) + "px";
            windowEl.style.top = (e.clientY - this.dragOffsetY) + "px";
            windowEl.style.right = "auto";
            windowEl.style.bottom = "auto";
        });

        document.addEventListener("mouseup", () => {
            this.dragging = false;
            document.body.style.userSelect = "";
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

        if (!message) return;

        input.value = "";
        input.style.height = "auto";

        const welcome = document.getElementById("erp-ai-welcome");
        if (welcome) welcome.style.display = "none";

        this.messages.push({ role: "user", content: message });
        this.addMessage(message, "user");

        this.showTyping();

        try {
            const response = await frappe.call({
                method: "erp_ai.api.ask",
                args: {
                    message: message,
                    conversation: JSON.stringify(this.messages.slice(0, -1))
                }
            });

            this.hideTyping();

            if (response && response.message && response.message.reply) {
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

    addMessage(text, sender) {
        const container = document.getElementById("erp-ai-messages");
        const row = document.createElement("div");
        row.className = "erp-ai-row " + sender;

        const avatar = document.createElement("div");
        avatar.className = "erp-ai-avatar";
        avatar.innerHTML = sender === "user" ? "👤" : "🤖";

        const bubble = document.createElement("div");
        bubble.className = "erp-ai-message " + sender;

        let cleanText = typeof text === "object" ? (text.reply || JSON.stringify(text)) : text;

        if (sender === "assistant") {
            const tableData = this.extractTableData(String(cleanText));
            
            if (tableData && tableData.length > 0) {
                let textParts = String(cleanText).split(/\|.*\|/);
                let textWithoutTable = textParts[0] ? textParts[0].trim() : "";
                
                let htmlOutput = `<div class="ai-text-part" style="margin-bottom: 10px;">${textWithoutTable}</div>`;
                
                htmlOutput += `<div class="table-responsive" style="margin-top: 8px; margin-bottom: 8px; overflow-x: auto;">
                    <table class="table table-bordered table-striped" style="width: 100%; background: #fff; font-size: 11px; color: #333; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f1f3f5;">`;
                
                let headers = Object.keys(tableData[0]);
                headers.forEach(h => {
                    htmlOutput += `<th style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${h}</th>`;
                });
                
                htmlOutput += `</tr></thead><tbody>`;
                
                tableData.forEach(row => {
                    htmlOutput += `<tr>`;
                    headers.forEach(h => {
                        htmlOutput += `<td style="padding: 6px 8px; border: 1px solid #dee2e6; text-align: right;">${row[h] || ''}</td>`;
                    });
                    htmlOutput += `</tr>`;
                });
                
                htmlOutput += `</tbody></table></div>`;

                let encodedData = encodeURIComponent(JSON.stringify(tableData));
                htmlOutput += `
                    <div class="message-actions" style="margin-top: 10px; clear: both; width: 100%;">
                        <button class="btn btn-xs btn-default export-csv-btn" onclick='downloadReportCSV(JSON.parse(decodeURIComponent("${encodedData}")))' style="cursor: pointer; background: #f8f9fa; border: 1px solid #cbd5d1; border-radius: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; gap: 6px; color: #2c3e50; width: 100%; box-sizing: border-box;">
                            <i class="fa fa-download"></i> Download (CSV)
                        </button>
                    </div>
                `;
                
                bubble.innerHTML = htmlOutput;
            } else {
                if (window.frappe && frappe.markdown) {
                    bubble.innerHTML = frappe.markdown(String(cleanText));
                } else {
                    bubble.innerText = String(cleanText);
                }
            }
        } else {
            bubble.innerText = String(cleanText);
        }

        if (sender === "user") {
            row.appendChild(bubble);
            row.appendChild(avatar);
        } else {
            row.appendChild(avatar);
            row.appendChild(bubble);
        }

        container.appendChild(row);
        this.scrollToBottom();
    }

    showTyping() {
        if (document.getElementById("erp-ai-typing")) return;
        const container = document.getElementById("erp-ai-messages");
        const row = document.createElement("div");
        row.id = "erp-ai-typing";
        row.className = "erp-ai-row assistant";
        row.innerHTML = `
            <div class="erp-ai-avatar">🤖</div>
            <div class="erp-ai-message assistant">
                <div class="erp-ai-loading-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        container.appendChild(row);
        this.scrollToBottom();
    }

    hideTyping() {
        const typing = document.getElementById("erp-ai-typing");
        if (typing) typing.remove();
    }

    scrollToBottom() {
        const body = document.getElementById("erp-ai-body");
        if (body) body.scrollTop = body.scrollHeight;
    }
}

$(function () {
    console.log("ERP AI Clean & Stable Version Loaded.");
    window.erp_ai = new ERPAI();
});

// دالة التحميل العامة
window.downloadReportCSV = function(jsonData, filename = "erp_report.csv") {
    if (typeof jsonData === "string") {
        try {
            jsonData = JSON.parse(jsonData);
        } catch (e) {
            console.error("Invalid JSON data");
            return;
        }
    }

    frappe.call({
        method: "erp_ai.api.export_data_to_csv",
        args: {
            data_json: jsonData,
            filename: filename
        },
        callback: function(r) {
            if (r.message && r.message.status === "success") {
                let blob = new Blob([r.message.filedata], { type: 'text/csv;charset=utf-8;' });
                let link = document.createElement("a");
                let url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", r.message.file_name);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                frappe.msgprint(__('حدث خطأ أثناء تصدير الملف'));
            }
        }
    });
};