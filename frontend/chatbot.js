document.addEventListener("DOMContentLoaded", () => {
  // DOM elements
  const chatButton = document.getElementById("chat-button");
  const chatWindow = document.getElementById("chat-window");
  const closeChat = document.getElementById("close-chat");
  const minimizeChat = document.getElementById("minimize-chat");
  const sendButton = document.getElementById("send-button");
  const chatInput = document.getElementById("chat-input");
  const chatMessages = document.getElementById("chat-messages");
  const fileInput = document.getElementById("file-input");
  const fileButton = document.getElementById("file-button");
  const minimizedLabel = chatWindow.querySelector(".minimized-label");

  // -----------------------------
  // Open chat
  // -----------------------------
  chatButton.addEventListener("click", () => {
    chatWindow.style.display = "block";        
    chatWindow.classList.remove("minimized");  
    chatButton.style.display = "none";         
    minimizedLabel?.classList.add("hidden");
  });

  // -----------------------------
  // Close chat (fully fixed)
  // -----------------------------
  closeChat.addEventListener("click", (e) => {
    e.stopPropagation();                 
    chatWindow.style.display = "none";   
    chatButton.style.display = "block";  
  });

  // -----------------------------
  // Escape key closes chat
  // -----------------------------
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && chatWindow.style.display !== "none") {
      chatWindow.style.display = "none";
      chatButton.style.display = "block";
    }
  });

  // -----------------------------
  // Minimize chat 
  // -----------------------------
  minimizeChat.addEventListener("click", (e) => {
    chatWindow.classList.toggle("minimized");
    if (chatWindow.classList.contains("minimized")) {
      minimizedLabel?.classList.remove("hidden");
    } else {
      minimizedLabel?.classList.add("hidden");
    }
    e.stopPropagation();
  });

  // Restore chat when clicking on minimized window
  chatWindow.addEventListener("click", (e) => {
    if (
      chatWindow.classList.contains("minimized") &&
      !e.target.closest("#minimize-chat") &&
      !e.target.closest("#close-chat")
    ) {
      chatWindow.classList.remove("minimized");
      minimizedLabel?.classList.add("hidden");
    }
  });

  // -----------------------------
  // File upload
  // -----------------------------
  fileButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    if (fileInput.files.length > 0) {
      await uploadFile(fileInput.files[0]);
      fileInput.value = "";
    }
  });

  chatWindow.addEventListener("dragover", (e) => e.preventDefault());
  chatWindow.addEventListener("drop", async (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  });

  // -----------------------------
  // Send message
  // -----------------------------
  sendButton.addEventListener("click", sendHandler);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendHandler();
    }
  });

  // -----------------------------
  // Message functions
  // -----------------------------
  function addMessage(text, sender, sources = null) {
    const msg = document.createElement("div");
    msg.classList.add("message", sender);

    const textDiv = document.createElement("div");
    textDiv.classList.add("text");
    textDiv.innerText = text;
    msg.appendChild(textDiv);

    if (sources && sources.length > 0) {
      const srcDiv = document.createElement("div");
      srcDiv.classList.add("sources");
      let listHtml = "<strong>Sources:</strong><br>";
      sources.forEach((src) => {
        if (typeof src === "object" && src.source) {
          if (src.source.startsWith("http")) {
            listHtml += `- <a href="${src.source}" target="_blank">${src.source}</a> (chunk ${src.chunk})<br>`;
          } else {
            listHtml += `- ${src.source} (chunk ${src.chunk})<br>`;
          }
        } else {
          listHtml += `- ${src}<br>`;
        }
      });
      srcDiv.innerHTML = listHtml;
      msg.appendChild(srcDiv);
    }

    chatMessages.appendChild(msg);
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" });
    return msg;
  }

  function showTyping() {
    const typingDiv = document.createElement("div");
    typingDiv.classList.add("typing");
    typingDiv.innerHTML = "<span></span><span></span><span></span>";
    typingDiv.id = "typing-indicator";
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTo({ top: chatMessages.scrollHeight });
  }

  function hideTyping() {
    const t = document.getElementById("typing-indicator");
    if (t) t.remove();
  }

  async function sendHandler() {
    const text = chatInput.value.trim();
    if (!text) return;

    addMessage(text, "user");
    chatInput.value = "";
    chatInput.focus();
    sendButton.disabled = true;
    showTyping();

    await sendMessage(text);

    hideTyping();
    sendButton.disabled = false;
  }

  async function sendMessage(input) {
    try {
      const formData = new FormData();
      formData.append("question", input);

      const res = await fetch("http://localhost:8000/ask/", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();
      addMessage(data.answer, "bot", data.sources || []);
    } catch (err) {
      console.error(err);
      addMessage("⚠️ Cannot reach server", "bot");
    }
  }

  async function uploadFile(file) {
    addMessage(`📂 Uploading ${file.name}...`, "bot");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("http://localhost:8000/upload-file/", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      addMessage(`✅ File uploaded successfully! (${data.chunks_inserted} chunks)`, "bot");
    } catch (err) {
      console.error(err);
      addMessage("⚠️ Cannot upload file", "bot");
    }
  }
});
