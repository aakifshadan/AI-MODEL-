async function sendMessage() {
    const input = document.getElementById("userInput");
    const chatBox = document.getElementById("chatBox");
    const model = document.getElementById("modelSelect").value;

    if (!input.value.trim()) return;

    // User message
    const userMsg = document.createElement("div");
    userMsg.className = "message user";
    userMsg.innerText = input.value;
    chatBox.appendChild(userMsg);

    const message = input.value;
    input.value = "";

    // Call backend
    const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, model })
    });

    const data = await res.json();

    // AI message
    const botMsg = document.createElement("div");
    botMsg.className = "message bot";
    botMsg.innerText = data.reply;

    chatBox.appendChild(botMsg);
    chatBox.scrollTop = chatBox.scrollHeight;
}