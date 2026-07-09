(() => {
  // ../erp_ai/erp_ai/public/js/erp_ai.bundle.js
  var ERPAI = class {
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
      if (!response.ok)
        throw new Error("Failed to load ERP AI template.");
      return await response.text();
    }
    createButton() {
      if (document.getElementById("erp-ai-button"))
        return;
      const button = document.createElement("div");
      button.id = "erp-ai-button";
      button.innerHTML = "\u{1F916}";
      document.body.appendChild(button);
      button.addEventListener("click", () => this.toggleWindow());
    }
    async createWindow() {
      if (document.getElementById("erp-ai-window"))
        return;
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
      input.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";
      });
      document.querySelectorAll(".erp-ai-suggestion").forEach((button) => {
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
        if (e.target.tagName === "BUTTON")
          return;
        this.dragging = true;
        const rect = windowEl.getBoundingClientRect();
        this.dragOffsetX = e.clientX - rect.left;
        this.dragOffsetY = e.clientY - rect.top;
        document.body.style.userSelect = "none";
      });
      document.addEventListener("mousemove", (e) => {
        if (!this.dragging)
          return;
        windowEl.style.left = e.clientX - this.dragOffsetX + "px";
        windowEl.style.top = e.clientY - this.dragOffsetY + "px";
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
      if (input)
        input.focus();
    }
    async sendMessage() {
      const input = document.getElementById("erp-ai-input");
      const message = input.value.trim();
      if (!message)
        return;
      input.value = "";
      input.style.height = "auto";
      const welcome = document.getElementById("erp-ai-welcome");
      if (welcome)
        welcome.style.display = "none";
      this.messages.push({ role: "user", content: message });
      this.addMessage(message, "user");
      this.showTyping();
      try {
        const response = await frappe.call({
          method: "erp_ai.api.ask",
          args: {
            message,
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
    addMessage(text, sender) {
      const container = document.getElementById("erp-ai-messages");
      const row = document.createElement("div");
      row.className = "erp-ai-row " + sender;
      const avatar = document.createElement("div");
      avatar.className = "erp-ai-avatar";
      avatar.innerHTML = sender === "user" ? "\u{1F464}" : "\u{1F916}";
      const bubble = document.createElement("div");
      bubble.className = "erp-ai-message " + sender;
      let cleanText = typeof text === "object" ? text.reply || JSON.stringify(text) : text;
      if (sender === "assistant" && window.frappe && frappe.markdown) {
        bubble.innerHTML = frappe.markdown(String(cleanText));
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
      if (document.getElementById("erp-ai-typing"))
        return;
      const container = document.getElementById("erp-ai-messages");
      const row = document.createElement("div");
      row.id = "erp-ai-typing";
      row.className = "erp-ai-row assistant";
      row.innerHTML = `
            <div class="erp-ai-avatar">\u{1F916}</div>
            <div class="erp-ai-message assistant">
                <div class="erp-ai-loading-dots"><span></span><span></span><span></span></div>
            </div>
        `;
      container.appendChild(row);
      this.scrollToBottom();
    }
    hideTyping() {
      const typing = document.getElementById("erp-ai-typing");
      if (typing)
        typing.remove();
    }
    scrollToBottom() {
      const body = document.getElementById("erp-ai-body");
      if (body)
        body.scrollTop = body.scrollHeight;
    }
  };
  $(function() {
    console.log("ERP AI Clean & Stable Version Loaded.");
    window.erp_ai = new ERPAI();
  });
})();
//# sourceMappingURL=erp_ai.bundle.EX52NLXO.js.map
