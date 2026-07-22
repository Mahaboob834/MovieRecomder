// Point this at your backend's URL if the frontend is hosted separately
// from the Flask app (e.g. frontend on Netlify, backend on Render).
// Leave as '' when the frontend is served BY the Flask app itself.
const API_BASE = '';

const feed = document.getElementById('feed');
const input = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const autocompleteEl = document.getElementById('autocomplete');
const greetingText = document.getElementById('greeting-text');

let autocompleteTimer = null;

async function loadGreeting() {
  try {
    const res = await fetch(`${API_BASE}/api/greeting`);
    const data = await res.json();
    greetingText.textContent = data.message;
  } catch (err) {
    greetingText.textContent = "Hi there! Ready to discover some movies?";
  }
}

function addYouLine(text) {
  const div = document.createElement('div');
  div.className = 'you-line';
  div.textContent = text;
  feed.appendChild(div);
  scrollFeedToBottom();
}

function addUsherLine(text) {
  const wrap = document.createElement('div');
  wrap.className = 'usher-line';
  wrap.innerHTML = `<span class="usher-badge">USHER</span><p></p>`;
  wrap.querySelector('p').textContent = text;
  feed.appendChild(wrap);
  scrollFeedToBottom();
  return wrap;
}

function addFilmstrip(recommendations, blurb) {
  const card = document.createElement('div');
  card.className = 'filmstrip';

  const list = recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('');
  card.innerHTML = `
    <div class="filmstrip-sprockets"></div>
    <div class="filmstrip-body">
      <ul>${list}</ul>
      ${blurb ? `<p class="blurb"></p>` : ''}
    </div>
    <div class="filmstrip-sprockets"></div>
  `;
  if (blurb) {
    card.querySelector('.blurb').textContent = blurb;
  }
  feed.appendChild(card);
  scrollFeedToBottom();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function scrollFeedToBottom() {
  feed.scrollTop = feed.scrollHeight;
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addYouLine(text);
  input.value = '';
  hideAutocomplete();
  sendBtn.disabled = true;

  const thinking = addUsherLine('Checking the projection booth…');

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();

    thinking.querySelector('p').textContent = data.reply;

    if (data.recommendations && data.recommendations.length) {
      addFilmstrip(data.recommendations, data.blurb);
    }
  } catch (err) {
    thinking.querySelector('p').textContent =
      "The projector jammed — couldn't reach the recommendation service.";
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

function hideAutocomplete() {
  autocompleteEl.hidden = true;
  autocompleteEl.innerHTML = '';
}

async function updateAutocomplete() {
  const q = input.value.trim();
  if (q.length < 2) {
    hideAutocomplete();
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.results || !data.results.length) {
      hideAutocomplete();
      return;
    }
    autocompleteEl.innerHTML = data.results
      .map(title => `<li>${escapeHtml(title)}</li>`)
      .join('');
    autocompleteEl.hidden = false;
  } catch (err) {
    hideAutocomplete();
  }
}

autocompleteEl.addEventListener('click', (e) => {
  if (e.target.tagName === 'LI') {
    input.value = e.target.textContent;
    hideAutocomplete();
    input.focus();
  }
});

input.addEventListener('input', () => {
  clearTimeout(autocompleteTimer);
  autocompleteTimer = setTimeout(updateAutocomplete, 200);
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMessage();
  if (e.key === 'Escape') hideAutocomplete();
});

sendBtn.addEventListener('click', sendMessage);

document.addEventListener('click', (e) => {
  if (!e.target.closest('.ticket-window') && !e.target.closest('.autocomplete')) {
    hideAutocomplete();
  }
});

loadGreeting();
