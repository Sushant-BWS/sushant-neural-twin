const titles = {
  chat: "Ask the twin",
  profile: "Profile",
  projects: "Projects",
  graph: "Knowledge graph",
  thoughts: "Thought profile",
  recruiter: "Recruiter mode",
};

const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");
const viewTitle = document.querySelector("#view-title");
const messageList = document.querySelector("#message-list");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const clearSession = document.querySelector("#clear-session");

function selectView(viewName) {
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === viewName));
  views.forEach((view) => view.classList.toggle("active", view.dataset.panel === viewName));
  viewTitle.textContent = titles[viewName];
}

navItems.forEach((item) => {
  item.addEventListener("click", () => selectView(item.dataset.view));
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  const userMessage = document.createElement("div");
  userMessage.className = "chat-message user-message";
  userMessage.textContent = message;
  messageList.appendChild(userMessage);

  const assistantMessage = document.createElement("div");
  assistantMessage.className = "chat-message assistant-message";
  assistantMessage.textContent = "I don't have enough verified information to answer that yet.";
  messageList.appendChild(assistantMessage);
  chatInput.value = "";
  messageList.scrollTop = messageList.scrollHeight;
});

clearSession.addEventListener("click", () => {
  messageList.innerHTML = `
    <div class="welcome-message">
      <div class="welcome-mark">SN</div>
      <div>
        <h3>Ready when the evidence is.</h3>
        <p>The assistant will answer from verified personal knowledge once source material is connected.</p>
      </div>
    </div>`;
});
