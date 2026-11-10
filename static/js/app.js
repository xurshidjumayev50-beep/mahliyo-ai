/**
 * Mahliyo AI — Front-End Application Logic v1.4
 * Features: Real-time chat, Voice Recognition, Speech Synthesis,
 * PPTX Slide Deck Generator & Viewer, Word DOCX Mustaqil Ish Viewer.
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM Elements ---
  const chatViewport = document.getElementById('chatViewport');
  const welcomeHero = document.getElementById('welcomeHero');
  const messagesContainer = document.getElementById('messagesContainer');
  const thinkingBubble = document.getElementById('thinkingBubble');
  const thinkingStatusText = document.getElementById('thinkingStatusText');
  
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const stopGeneratingBtn = document.getElementById('stopGeneratingBtn');
  const internetToggleBtn = document.getElementById('internetToggleBtn');
  const micBtn = document.getElementById('micBtn');
  const attachmentBtn = document.getElementById('attachmentBtn');
  const fileInput = document.getElementById('fileInput');
  const filePreviewBar = document.getElementById('filePreviewBar');
  const attachedFileName = document.getElementById('attachedFileName');
  const removeAttachmentBtn = document.getElementById('removeAttachmentBtn');
  const voiceRecordingBanner = document.getElementById('voiceRecordingBanner');
  const stopVoiceBtn = document.getElementById('stopVoiceBtn');

  const newChatBtn = document.getElementById('newChatBtn');
  const mobileNewChatBtn = document.getElementById('mobileNewChatBtn');
  const quickSlideBtn = document.getElementById('quickSlideBtn');
  const quickDocBtn = document.getElementById('quickDocBtn');
  const quickExcelBtn = document.getElementById('quickExcelBtn');
  const quickImageBtn = document.getElementById('quickImageBtn');
  const quickVideoBtn = document.getElementById('quickVideoBtn');
  const openTranslatorBtn = document.getElementById('openTranslatorBtn');
  const translatorModal = document.getElementById('translatorModal');
  const closeTranslatorBtn = document.getElementById('closeTranslatorBtn');
  const translateSource = document.getElementById('translateSource');
  const translateTarget = document.getElementById('translateTarget');
  const swapTranslateLanguagesBtn = document.getElementById('swapTranslateLanguages');
  const translateInput = document.getElementById('translateInput');
  const translateOutput = document.getElementById('translateOutput');
  const translateBtn = document.getElementById('translateBtn');
  const copyTranslationBtn = document.getElementById('copyTranslationBtn');
  const speakTranslationBtn = document.getElementById('speakTranslationBtn');
  const translatorStatus = document.getElementById('translatorStatus');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const chatHistoryList = document.getElementById('chatHistoryList');
  const currentChatTitle = document.getElementById('currentChatTitle');

  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  // Word Document Viewer Modal
  const wordViewerModal = document.getElementById('wordViewerModal');
  const wordModalTitle = document.getElementById('wordModalTitle');
  const wordModalDownloadBtn = document.getElementById('wordModalDownloadBtn');
  const wordModalPrintBtn = document.getElementById('wordModalPrintBtn');
  const closeWordModalBtn = document.getElementById('closeWordModalBtn');
  const wordViewerBody = document.getElementById('wordViewerBody');

  // Slide Viewer Modal
  const slideViewerModal = document.getElementById('slideViewerModal');
  const slideModalTitle = document.getElementById('slideModalTitle');
  const slideModalDownloadBtn = document.getElementById('slideModalDownloadBtn');
  const closeSlideModalBtn = document.getElementById('closeSlideModalBtn');
  const slideCanvas = document.getElementById('slideCanvas');
  const prevSlideBtn = document.getElementById('prevSlideBtn');
  const nextSlideBtn = document.getElementById('nextSlideBtn');
  const slideCounter = document.getElementById('slideCounter');

  // Settings Modal elements
  const openSettingsBtn = document.getElementById('openSettingsBtn');
  const topSettingsBtn = document.getElementById('topSettingsBtn');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const settingsModal = document.getElementById('settingsModal');
  const geminiApiKeyInput = document.getElementById('geminiApiKey');
  const toggleApiKeyVisBtn = document.getElementById('toggleApiKeyVisBtn');
  const modelSelect = document.getElementById('modelSelect');
  const systemPromptInput = document.getElementById('systemPromptInput');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const testKeyBtn = document.getElementById('testKeyBtn');
  const keyStatusAlert = document.getElementById('keyStatusAlert');
  const modelStatusTag = document.getElementById('modelStatusTag');
  const guestName = document.getElementById('guestName');
  const authModal = document.getElementById('authModal');
  const closeAuthModalBtn = document.getElementById('closeAuthModalBtn');
  const authTabs = document.querySelectorAll('[data-auth-tab]');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const authMessageWrap = document.querySelector('.auth-message-wrap');
  const authStatusAlert = document.getElementById('authStatusAlert');

  // --- State ---
  let activeChatId = null;
  let conversations = [];
  let authUser = null;
  let attachedFile = null;
  let isGenerating = false;
  let isRecordingVoice = false;
  let speechRecognition = null;
  let currentSpeakingUtterance = null;
  let activeChatAbortController = null;
  let useSearch = localStorage.getItem('mahliyo_use_search') === 'true';

  // Active slide deck state
  let currentSlideDeck = [];
  let currentSlideIndex = 0;

  if (internetToggleBtn) {
    function updateInternetToggle() {
      internetToggleBtn.classList.toggle('active', useSearch);
      internetToggleBtn.setAttribute('aria-pressed', String(useSearch));
      internetToggleBtn.title = useSearch
        ? 'Internet qidiruvi yoqilgan'
        : "Google Search orqali internetdan qidirish";
    }

    updateInternetToggle();
    internetToggleBtn.addEventListener('click', () => {
      useSearch = !useSearch;
      localStorage.setItem('mahliyo_use_search', String(useSearch));
      updateInternetToggle();
    });
  }

  // --- Speech Recognition Setup ---
  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognitionAPI) {
    speechRecognition = new SpeechRecognitionAPI();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'uz-UZ';

    speechRecognition.onstart = () => {
      isRecordingVoice = true;
      micBtn.classList.add('recording');
      voiceRecordingBanner.style.display = 'flex';
    };

    speechRecognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (finalTranscript) {
        messageInput.value = (messageInput.value + ' ' + finalTranscript).trim();
      } else if (interimTranscript) {
        messageInput.placeholder = interimTranscript;
      }
      messageInput.style.height = 'auto';
      messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
    };

    speechRecognition.onerror = (event) => {
      console.warn("Nutqni aniqlash xatosi:", event.error);
      stopVoiceRecording();
    };

    speechRecognition.onend = () => {
      stopVoiceRecording();
    };
  }

  function toggleVoiceRecording() {
    if (!speechRecognition) {
      alert("Brauzeringizda ovozni aniqlash (Speech Recognition) qo'llab-quvvatlanmaydi. Chrome yoki Edge brauzeridan foydalaning.");
      return;
    }

    if (isRecordingVoice) {
      speechRecognition.stop();
      stopVoiceRecording();
    } else {
      try {
        speechRecognition.start();
      } catch (err) {
        console.error("Mic start error:", err);
      }
    }
  }

  function stopVoiceRecording() {
    isRecordingVoice = false;
    micBtn.classList.remove('recording');
    voiceRecordingBanner.style.display = 'none';
    messageInput.placeholder = "Mahliyo'ga yozing yoki ovoz bilan ayting...";
  }

  micBtn.addEventListener('click', toggleVoiceRecording);
  stopVoiceBtn.addEventListener('click', () => {
    if (speechRecognition) speechRecognition.stop();
    stopVoiceRecording();
  });

  // --- Seed Initial Conversations (matching screenshot) ---
  const defaultSeeds = [
    {
      id: 'seed-1',
      title: 'Rekursiya va iteratsiya farqi',
      messages: [
        { role: 'user', content: 'Rekursiya va iteratsiya farqini tushuntirib ber.' },
        { 
          role: 'assistant', 
          content: '### Rekursiya va Iteratsiya Farqi\n\n- **Iteratsiya:** Sikl (`for`, `while`) orqali kod blokini takrorlash.\n- **Rekursiya:** Funksiya o\'zini o\'zi chaqirishi va to\'xtash shartiga (`base case`) ega bo\'lishi.\n\n```python\n# Iteratsiya\ndef faktorial_iter(n):\n    natija = 1\n    for i in range(1, n + 1):\n        natija *= i\n    return natija\n\n# Rekursiya\ndef faktorial_rek(n):\n    if n <= 1:\n        return 1\n    return n * faktorial_rek(n - 1)\n```' 
        }
      ]
    },
    {
      id: 'seed-2',
      title: 'Dekanatga ariza matni',
      messages: [
        { role: 'user', content: 'Dekanatga o\'qishni masofaviy davom ettirish bo\'yicha ariza yozib ber.' },
        { 
          role: 'assistant', 
          content: '```text\nMuhammad al-Xorazmiy nomidagi TATU\nKompyuter injiniringi fakulteti dekani\n[Dekan F.I.Sh.]ga\n3-bosqich talabasi [Ism Familiya]dan\n\nARIZA\n\nMen ushbu arizani yozishimdan maqsad shuki, oilaviy sharoitim sababli darslarni ma\'lum muddat erkin grafikda topshirishimga ruxsat berishingizni so\'rayman.\n\nSana: 30.10.2026\nImzo: __________\n```' 
        }
      ]
    },
    {
      id: 'seed-3',
      title: 'Ekologiya taqdimoti rejasi',
      messages: [
        { role: 'user', content: 'Ekologiya taqdimoti rejasi' },
        { role: 'assistant', content: '1. Kirish: Sayyoramiz va ekologik vaziyat\n2. Orol dengizi muammosi va uning ta\'siri\n3. Yashil energiya va quyosh panellari\n4. Chiqindilarni qayta ishlash\n5. Xulosa va har birimizning vazifamiz' }
      ]
    },
    {
      id: 'seed-4',
      title: 'Inglizcha xatni tarjima qilish',
      messages: [
        { role: 'user', content: 'Dear hiring manager, I am writing to express my interest in the Software Engineer position.' },
        { role: 'assistant', content: '**Tarjima:**\n\nHurmatli ishga qabul qiluvchi menejer,\nMen Dasturiy ta\'minot muhandisi (Software Engineer) lavozimiga qiziqishimni bildirish uchun ushbu xatni yozyapman.' }
      ]
    }
  ];

  // --- LocalStorage Helpers ---
  function loadStoredSettings() {
    const key = localStorage.getItem('mahliyo_gemini_key') || '';
    const savedModel = localStorage.getItem('mahliyo_model');
    const model = savedModel === 'gemini-3.5-flash'
      ? savedModel
      : 'gemini-3.5-flash';
    const prompt = localStorage.getItem('mahliyo_system_prompt') || '';

    localStorage.setItem('mahliyo_model', model);
    geminiApiKeyInput.value = key;
    modelSelect.value = model;
    systemPromptInput.value = prompt;

    updateModelTag(key, model);
  }

  function updateModelTag(key, model) {
    if (key && key.trim()) {
      modelStatusTag.textContent = model.replace('gemini-', 'Gemini ').split('-')[0] + ' (Faol)';
      modelStatusTag.style.color = 'var(--color-primary)';
    } else {
      modelStatusTag.textContent = 'Mahliyo v1.4 · .env kaliti';
      modelStatusTag.style.color = '#fbbf24';
    }
  }

  function loadGuestConversations() {
    const saved = localStorage.getItem('mahliyo_conversations');
    if (saved) {
      try {
        conversations = JSON.parse(saved);
      } catch (e) {
        conversations = defaultSeeds;
      }
    } else {
      conversations = defaultSeeds;
      saveConversations();
    }
    renderHistoryList();
  }

  function saveConversations(chat = null) {
    if (!authUser) {
      localStorage.setItem('mahliyo_conversations', JSON.stringify(conversations));
      return;
    }
    if (!chat) return;

    fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(chat)
    }).then(async (response) => {
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Suhbatni saqlab bo‘lmadi.');
      }
    }).catch((error) => {
      console.error('Suhbatni saqlash xatosi:', error);
    });
  }

  function updateAuthUi() {
    guestName.textContent = authUser ? authUser.email : 'Mehmon rejimi';
    openSettingsBtn.textContent = authUser ? 'Chiqish' : 'Kirish';
    openSettingsBtn.title = authUser ? 'Akkauntdan chiqish' : 'Akkauntga kirish';
  }

  async function loadAccountConversations() {
    const response = await fetch('/api/conversations');
    if (!response.ok) throw new Error('Akkaunt suhbatlarini yuklab bo‘lmadi.');
    conversations = (await response.json()).map((chat) => ({ ...chat }));
    renderHistoryList();
    startNewChat();
  }

  async function initializeAuth() {
    try {
      const response = await fetch('/api/auth/me');
      const data = await response.json();
      authUser = data.authenticated ? data.user : null;
      updateAuthUi();
      if (authUser) await loadAccountConversations();
    } catch (error) {
      console.error('Akkaunt holatini tekshirish xatosi:', error);
    }
  }

  // --- History UI Rendering ---
  function renderHistoryList() {
    chatHistoryList.innerHTML = '';
    conversations.forEach((chat) => {
      const item = document.createElement('div');
      item.className = `history-item ${chat.id === activeChatId ? 'active' : ''}`;
      item.innerHTML = `
        <span class="history-item-title">${escapeHtml(chat.title)}</span>
        <button class="history-item-del" data-id="${chat.id}" title="O'chirish">&times;</button>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('history-item-del')) return;
        selectConversation(chat.id);
        closeMobileSidebar();
      });

      const delBtn = item.querySelector('.history-item-del');
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteConversation(chat.id);
      });

      chatHistoryList.appendChild(item);
    });
  }

  async function selectConversation(id) {
    activeChatId = id;
    const chat = conversations.find(c => c.id === id);
    if (!chat) return;

    if (authUser && !Array.isArray(chat.messages)) {
      try {
        const response = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Suhbatni yuklab bo‘lmadi.');
        chat.messages = data.messages;
      } catch (error) {
        console.error('Suhbatni yuklash xatosi:', error);
        return;
      }
      if (activeChatId !== id) return;
    }

    currentChatTitle.textContent = chat.title;
    renderHistoryList();

    if (chat.messages && chat.messages.length > 0) {
      welcomeHero.style.display = 'none';
      messagesContainer.innerHTML = '';
      chat.messages.forEach(msg => appendMessageDOM(msg.role, msg.content, msg.artifact, null, msg.sources));
      scrollChatToBottom();
    } else {
      startNewChat();
    }
  }

  function deleteConversation(id) {
    if (authUser) {
      fetch(`/api/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
        .then(async (response) => {
          if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Suhbatni o‘chirib bo‘lmadi.');
          }
        })
        .catch((error) => console.error('Suhbatni o‘chirish xatosi:', error));
    }
    conversations = conversations.filter(c => c.id !== id);
    if (!authUser) saveConversations();
    if (activeChatId === id) {
      startNewChat();
    } else {
      renderHistoryList();
    }
  }

  function startNewChat() {
    activeChatId = 'chat-' + Date.now();
    currentChatTitle.textContent = 'Yangi suhbat';
    welcomeHero.style.display = 'flex';
    messagesContainer.innerHTML = '';
    renderHistoryList();
    messageInput.value = '';
    messageInput.style.height = 'auto';
    clearAttachment();
    messageInput.focus();
  }

  // --- Message DOM Rendering ---
  function appendMessageDOM(role, text, artifact = null, imageUrl = null, sources = []) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    if (role === 'assistant') {
      let artifactHtml = '';

      if (artifact) {
        if (artifact.type === 'presentation') {
          artifactHtml = `
            <div class="artifact-card presentation">
              <div class="artifact-info">
                <div class="artifact-badge-icon">P</div>
                <div>
                  <div class="artifact-title">📊 Taqdimot Slaydi (.pptx)</div>
                  <div class="artifact-subtitle">${escapeHtml(artifact.topic || 'Slayd')}</div>
                </div>
              </div>
              <div class="artifact-actions">
                <button type="button" class="btn-artifact-view view-slide-btn">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  Ko'rish
                </button>
                <a href="${artifact.file_url}" class="btn-artifact-download" download>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  PPTX Yuklab olish
                </a>
              </div>
            </div>
          `;
        } else if (artifact.type === 'document') {
          artifactHtml = `
            <div class="artifact-card document">
              <div class="artifact-info">
                <div class="artifact-badge-icon">W</div>
                <div>
                  <div class="artifact-title">📝 Mustaqil Ish Hujjati (.docx)</div>
                  <div class="artifact-subtitle">${escapeHtml(artifact.topic || 'Mustaqil ish')} • OTM Standarti</div>
                </div>
              </div>
              <div class="artifact-actions">
                <button type="button" class="btn-artifact-view view-doc-btn">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  O'qish
                </button>
                <a href="${artifact.file_url}" class="btn-artifact-download" download>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  DOCX Yuklab olish
                </a>
              </div>
            </div>
          `;
        } else if (artifact.type === 'spreadsheet') {
          const sheetPreviews = (artifact.sheets || []).map((sheet) => {
            const headerHtml = (sheet.columns || [])
              .map((column) => `<th>${escapeHtml(String(column))}</th>`)
              .join('');
            const rowHtml = (sheet.rows || []).slice(0, 10).map((cells) => `
              <tr>${cells.map((value) => `<td>${escapeHtml(String(value ?? ''))}</td>`).join('')}</tr>
            `).join('');
            return `
              <div class="spreadsheet-sheet-preview">
                <div class="spreadsheet-sheet-name">${escapeHtml(sheet.name || 'Jadval')}</div>
                <div class="spreadsheet-table-scroll">
                  <table class="spreadsheet-preview-table">
                    <thead><tr>${headerHtml}</tr></thead>
                    <tbody>${rowHtml}</tbody>
                  </table>
                </div>
              </div>
            `;
          }).join('');
          artifactHtml = `
            <div class="artifact-card spreadsheet">
              <div class="artifact-info">
                <div class="artifact-badge-icon">X</div>
                <div>
                  <div class="artifact-title">📈 Excel jadval (.xlsx)</div>
                  <div class="artifact-subtitle">${escapeHtml(artifact.topic || 'Jadval')}</div>
                </div>
              </div>
              <div class="spreadsheet-previews">${sheetPreviews}</div>
              <div class="artifact-actions">
                <a href="${escapeHtml(artifact.file_url)}" class="btn-artifact-download" download="${escapeHtml(artifact.filename || 'jadval.xlsx')}">
                  XLSX Yuklab olish
                </a>
              </div>
            </div>
          `;
        } else if (artifact.type === 'image') {
          artifactHtml = `
            <div class="generated-image-card">
              <img src="${escapeHtml(artifact.file_url)}" alt="Mahliyo yaratgan rasm">
              <a href="${escapeHtml(artifact.file_url)}" download="${escapeHtml(artifact.filename || 'mahliyo-rasm.png')}">
                Rasmni yuklab olish
              </a>
            </div>
          `;
        } else if (artifact.type === 'video') {
          artifactHtml = `
            <div class="generated-image-card generated-video-card">
              <video controls preload="metadata" src="${escapeHtml(artifact.media_url)}" aria-label="Mahliyo yaratgan video"></video>
              <a href="${escapeHtml(artifact.file_url)}" download="${escapeHtml(artifact.filename || 'mahliyo-video.mp4')}">
                Videoni yuklab olish
              </a>
            </div>
          `;
        }
      }

      row.innerHTML = `
        <div class="msg-avatar bot">
          <img src="/static/images/logo.svg" alt="Mahliyo">
        </div>
        <div class="message-bubble">
          <div class="msg-body">${formatMarkdown(text)}</div>
          ${renderSourcesBlock(sources)}
          ${artifactHtml}
          <div class="msg-actions">
            <button class="btn-msg-action copy-msg-btn">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Nusxa olish
            </button>
            <button class="btn-msg-action tts-msg-btn">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
              </svg>
              <span>Ovozli eshitish</span>
            </button>
          </div>
        </div>
      `;

      // Copy text button
      const copyBtn = row.querySelector('.copy-msg-btn');
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(row.dataset.messageText || '').then(() => {
          copyBtn.textContent = "Nusxa olindi!";
          setTimeout(() => {
            copyBtn.innerHTML = `
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg> Nusxa olish`;
          }, 2000);
        });
      });

      // TTS (Speech synthesis) button
      const ttsBtn = row.querySelector('.tts-msg-btn');
      ttsBtn.addEventListener('click', () => {
        speakText(row.dataset.messageText || '', ttsBtn);
      });

      // Artifact view handlers
      if (artifact) {
        if (artifact.type === 'presentation') {
          const viewSlideBtn = row.querySelector('.view-slide-btn');
          if (viewSlideBtn) {
            viewSlideBtn.addEventListener('click', () => {
              openSlideModal(artifact);
            });
          }
        } else if (artifact.type === 'document') {
          const viewDocBtn = row.querySelector('.view-doc-btn');
          if (viewDocBtn) {
            viewDocBtn.addEventListener('click', () => {
              openWordModal(artifact);
            });
          }
        }
      }

    } else {
      // User message
      row.innerHTML = `
        <div class="message-bubble">
          <div class="msg-body">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
        </div>
      `;
      if (imageUrl) {
        const image = document.createElement('img');
        image.className = 'attached-image-preview';
        image.src = imageUrl;
        image.alt = 'Suhbatga biriktirilgan rasm';
        image.addEventListener('load', () => URL.revokeObjectURL(imageUrl), { once: true });
        image.addEventListener('error', () => URL.revokeObjectURL(imageUrl), { once: true });
        row.querySelector('.message-bubble').appendChild(image);
      }
    }

    messagesContainer.appendChild(row);

    // Highlight code blocks
    row.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
      addCodeCopyBtn(block);
    });

    scrollChatToBottom();
    if (role === 'assistant') {
      row.dataset.messageText = text;
    }
    return row;
  }

  function updateStreamingMessage(row, text, sources = []) {
    row.dataset.messageText = text;
    const body = row.querySelector('.msg-body');
    body.innerHTML = formatMarkdown(text);
    row.querySelector('.sources-block')?.remove();
    body.insertAdjacentHTML('afterend', renderSourcesBlock(sources));
    row.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
      addCodeCopyBtn(block);
    });
    scrollChatToBottom();
  }

  function renderSourcesBlock(sources) {
    if (!Array.isArray(sources) || !sources.length) return '';
    const links = sources.map((source) => {
      if (!source || typeof source.url !== 'string') return '';
      let url;
      try {
        url = new URL(source.url);
      } catch {
        return '';
      }
      if (!['http:', 'https:'].includes(url.protocol)) return '';
      const title = typeof source.title === 'string' && source.title.trim()
        ? source.title
        : url.hostname;
      return `<li><a href="${escapeHtml(url.href)}" target="_blank" rel="noopener">${escapeHtml(title)}</a></li>`;
    }).filter(Boolean);
    if (!links.length) return '';
    return `<div class="sources-block"><strong>Manbalar</strong><ul>${links.join('')}</ul></div>`;
  }

  function addCodeCopyBtn(block) {
    const pre = block.parentElement;
    if (pre.querySelector('.code-copy-btn')) return;

    pre.style.position = 'relative';
    const btn = document.createElement('button');
    btn.className = 'code-copy-btn';
    btn.textContent = 'Nusxa';
    btn.style.cssText = `
      position: absolute;
      top: 6px;
      right: 8px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid var(--border-subtle);
      color: #94a3b8;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
    `;

    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(block.innerText).then(() => {
        btn.textContent = 'Olindi!';
        setTimeout(() => { btn.textContent = 'Nusxa'; }, 1500);
      });
    });

    pre.appendChild(btn);
  }

  function formatMarkdown(content) {
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(content);
    }
    return escapeHtml(content).replace(/\n/g, '<br>');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.innerText = str;
    return div.innerHTML;
  }

  function scrollChatToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  // --- Text-to-Speech (Mahliyo's Voice) ---
  function speakText(text, btnElement, language = 'uz-UZ') {
    if (!('speechSynthesis' in window)) {
      alert("Brauzeringizda nutq sintezi qo'llab-quvvatlanmaydi.");
      return;
    }

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = btnElement.dataset.idleLabel || "Ovozli eshitish";
      }
      return;
    }

    // Strip markdown formatting symbols for natural reading
    const clean = text.replace(/[#*`_~\[\]\(\)\>]/g, ' ').replace(/\n+/g, '. ');
    const utter = new SpeechSynthesisUtterance(clean);
    utter.lang = language;
    utter.rate = 1.0;
    utter.pitch = 1.05;

    // Pick a pleasant voice if available
    const voices = window.speechSynthesis.getVoices();
    const languagePrefix = language.split('-')[0].toLowerCase();
    const preferredVoice = voices.find(v => v.lang.toLowerCase().startsWith(languagePrefix))
      || voices.find(v => v.lang.startsWith('uz') || v.lang.startsWith('tr') || v.lang.startsWith('ru'));
    if (preferredVoice) utter.voice = preferredVoice;

    if (btnElement) {
      btnElement.classList.add('playing');
      btnElement.querySelector('span').textContent = "To'xtatish";
    }

    utter.onend = () => {
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = btnElement.dataset.idleLabel || "Ovozli eshitish";
      }
    };

    utter.onerror = () => {
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = btnElement.dataset.idleLabel || "Ovozli eshitish";
      }
    };

    window.speechSynthesis.speak(utter);
  }

  // --- Modals for Word & Slides ---
  function openWordModal(artifact) {
    wordModalTitle.textContent = `Mustaqil Ish — ${artifact.topic || 'Word Hujjati'}`;
    wordModalDownloadBtn.href = artifact.file_url;
    wordViewerBody.innerHTML = artifact.html_preview || '<p>Hujjat yuklanmoqda...</p>';
    wordViewerModal.style.display = 'flex';
  }

  closeWordModalBtn.addEventListener('click', () => {
    wordViewerModal.style.display = 'none';
  });

  wordModalPrintBtn.addEventListener('click', () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>${wordModalTitle.textContent}</title>
          <link rel="stylesheet" href="/static/css/style.css">
          <style>
            body { background: white !important; color: black !important; }
            .word-doc-paper { box-shadow: none !important; width: 100% !important; padding: 20px !important; }
          </style>
        </head>
        <body>
          ${wordViewerBody.innerHTML}
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); }, 500);
  });

  function openSlideModal(artifact) {
    currentSlideDeck = artifact.slides || [];
    currentSlideIndex = 0;
    slideModalTitle.textContent = `Taqdimot Slaydlari — ${artifact.topic || 'Slayd'}`;
    slideModalDownloadBtn.href = artifact.file_url;
    renderCurrentSlide();
    slideViewerModal.style.display = 'flex';
  }

  function renderCurrentSlide() {
    if (!currentSlideDeck || currentSlideDeck.length === 0) return;
    const slide = currentSlideDeck[currentSlideIndex];
    slideCounter.textContent = `${currentSlideIndex + 1} / ${currentSlideDeck.length}`;

    if (slide.type === 'title') {
      slideCanvas.innerHTML = `
        <div class="slide-title-view">
          <h1>${escapeHtml(slide.title)}</h1>
          <p>${escapeHtml(slide.subtitle || '')}</p>
          <div class="slide-meta">${escapeHtml(slide.author || '')} • ${escapeHtml(slide.date || '')}</div>
        </div>
      `;
    } else {
      const itemsHtml = (slide.items || []).map(it => `<li>${escapeHtml(it)}</li>`).join('');
      const subHtml = slide.subtitle ? `<p style="color: var(--color-moon); margin-top: 14px; font-weight: bold;">${escapeHtml(slide.subtitle)}</p>` : '';
      slideCanvas.innerHTML = `
        <h2>${escapeHtml(slide.title)}</h2>
        <ul>${itemsHtml}</ul>
        ${subHtml}
      `;
    }
  }

  prevSlideBtn.addEventListener('click', () => {
    if (currentSlideIndex > 0) {
      currentSlideIndex--;
      renderCurrentSlide();
    }
  });

  nextSlideBtn.addEventListener('click', () => {
    if (currentSlideIndex < currentSlideDeck.length - 1) {
      currentSlideIndex++;
      renderCurrentSlide();
    }
  });

  closeSlideModalBtn.addEventListener('click', () => {
    slideViewerModal.style.display = 'none';
  });

  // --- Quick Tools in Sidebar ---
  quickSlideBtn.addEventListener('click', () => {
    closeMobileSidebar();
    const topic = prompt("Taqdimot (slayd) mavzusini kiriting:", "Sun'iy intellekt va uning istiqbollari");
    if (topic && topic.trim()) {
      messageInput.value = `Menga quyidagi mavzuda professional taqdimot (slayd) va .pptx fayl tayyorlab ber: ${topic.trim()}`;
      handleSend();
    }
  });

  quickDocBtn.addEventListener('click', () => {
    closeMobileSidebar();
    const topic = prompt("Mustaqil ish (Word .docx) mavzusini kiriting:", "Zamonaviy dasturlash tillari va ularning tahlili");
    if (topic && topic.trim()) {
      messageInput.value = `Menga OTM standarti bo'yicha to'liq mustaqil ish (Word .docx) yozib ber: ${topic.trim()}`;
      handleSend();
    }
  });

  quickExcelBtn.addEventListener('click', () => {
    closeMobileSidebar();
    const topic = prompt("Excel jadval mavzusini kiriting:", "Oylik daromad va xarajatlar");
    if (topic && topic.trim()) {
      messageInput.value = `Excel jadval tuzib ber: ${topic.trim()}`;
      handleSend();
    }
  });

  quickImageBtn.addEventListener('click', () => {
    closeMobileSidebar();
    const prompt = window.prompt("Qanday rasm yaratilsin?", "Tog'lar ustidagi quyosh botishi, fotorealistik uslubda");
    if (prompt && prompt.trim()) {
      messageInput.value = `Rasm yarat: ${prompt.trim()}`;
      handleSend();
    }
  });

  quickVideoBtn.addEventListener('click', () => {
    closeMobileSidebar();
    const prompt = window.prompt("Qanday video yaratilsin?", "Tog'lar ustidan uchayotgan burgut, kinematik uslubda");
    if (prompt && prompt.trim()) {
      messageInput.value = `Video yarat: ${prompt.trim()}`;
      handleSend();
    }
  });

  openTranslatorBtn.addEventListener('click', () => {
    translatorModal.style.display = 'flex';
    translatorStatus.textContent = '';
    closeMobileSidebar();
    translateInput.focus();
  });

  closeTranslatorBtn.addEventListener('click', () => {
    translatorModal.style.display = 'none';
  });

  translatorModal.addEventListener('click', (event) => {
    if (event.target === translatorModal) translatorModal.style.display = 'none';
  });

  swapTranslateLanguagesBtn.addEventListener('click', () => {
    const previousSource = translateSource.value;
    const previousTarget = translateTarget.value;
    translateSource.value = previousTarget;
    translateTarget.value = previousSource === 'auto'
      ? (previousTarget === 'uz-Latn' ? 'en' : 'uz-Latn')
      : previousSource;
    translatorStatus.textContent = previousSource === 'auto'
      ? "Avto manba tili almashtirildi; kerakli maqsad tilini tanlang."
      : '';
  });

  translateBtn.addEventListener('click', async () => {
    const text = translateInput.value;
    if (!text.trim()) {
      translatorStatus.textContent = 'Tarjima uchun matn kiriting.';
      return;
    }

    translateBtn.disabled = true;
    translatorStatus.textContent = 'Tarjima qilinmoqda...';
    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          source: translateSource.value,
          target: translateTarget.value
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Tarjima bajarilmadi.');
      translateOutput.value = data.translation;
      translatorStatus.textContent = 'Tarjima tayyor.';
    } catch (error) {
      translatorStatus.textContent = error.message;
    } finally {
      translateBtn.disabled = false;
    }
  });

  copyTranslationBtn.addEventListener('click', async () => {
    if (!translateOutput.value) {
      translatorStatus.textContent = 'Avval matnni tarjima qiling.';
      return;
    }
    try {
      await navigator.clipboard.writeText(translateOutput.value);
      translatorStatus.textContent = 'Tarjima nusxalandi.';
    } catch (error) {
      translateOutput.focus();
      translateOutput.select();
      if (document.execCommand('copy')) {
        translatorStatus.textContent = 'Tarjima nusxalandi.';
      } else {
        translatorStatus.textContent = 'Nusxa olib bo‘lmadi. Matnni qo‘lda belgilang.';
      }
    }
  });

  speakTranslationBtn.dataset.idleLabel = 'Eshitish';
  speakTranslationBtn.addEventListener('click', () => {
    if (!translateOutput.value) {
      translatorStatus.textContent = 'Avval matnni tarjima qiling.';
      return;
    }
    const speechLanguages = {
      'uz-Latn': 'uz-UZ',
      'uz-Cyrl': 'uz-UZ',
      en: 'en-US',
      ru: 'ru-RU',
      tr: 'tr-TR'
    };
    speakText(translateOutput.value, speakTranslationBtn, speechLanguages[translateTarget.value]);
  });

  // --- Sending Message & Chat API ---
  async function readChatStream(response, onText) {
    if (!response.body) throw new Error('Brauzer javob oqimini qo‘llab-quvvatlamaydi.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let result = '';
    let sources = [];

    function processEvent(block) {
      const eventName = block.split('\n').find(line => line.startsWith('event:'))?.slice(6).trim();
      const data = block.split('\n')
        .filter(line => line.startsWith('data:'))
        .map(line => line.slice(5).trim())
        .join('\n');
      if (!data) return;
      const payload = JSON.parse(data);
      if (eventName === 'error' || payload.error) {
        throw new Error(payload.error || 'Javob oqimi xatosi.');
      }
      if (eventName === 'chunk' && typeof payload.text === 'string') {
        result += payload.text;
        onText(payload.text, result);
      } else if (eventName === 'sources' && Array.isArray(payload.sources)) {
        sources = payload.sources;
      }
    }

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, '\n');
      let separator = buffer.indexOf('\n\n');
      while (separator !== -1) {
        processEvent(buffer.slice(0, separator));
        buffer = buffer.slice(separator + 2);
        separator = buffer.indexOf('\n\n');
      }
      if (done) break;
    }
    if (buffer.trim()) processEvent(buffer);
    if (!result) throw new Error('Javob oqimida matn kelmadi.');
    return { text: result, sources };
  }

  async function requestLegacyChat(payload, signal) {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal
    });
    return { response, data: await response.json() };
  }

  async function handleSend() {
    const rawText = messageInput.value.trim();
    if (!rawText && !attachedFile) return;
    if (isGenerating) return;

    const attachedImage = attachedFile && attachedFile.type.startsWith('image/') ? attachedFile : null;
    if (attachedImage && !['image/jpeg', 'image/png', 'image/webp'].includes(attachedImage.type)) {
      alert("Faqat JPEG, PNG yoki WebP formatidagi rasmlar qo'llab-quvvatlanadi.");
      return;
    }
    if (attachedImage && attachedImage.size > 5 * 1024 * 1024) {
      alert("Rasm hajmi 5 MB dan oshmasligi kerak.");
      return;
    }

    let finalPrompt = rawText || (attachedImage ? "Iltimos, ushbu rasmni tahlil qilib bering." : '');
    if (attachedFile) {
      finalPrompt = `[Ilova qilingan fayl: ${attachedFile.name}]\n` + finalPrompt;
    }

    // Hide welcome hero on first message
    welcomeHero.style.display = 'none';

    // Append User Message
    appendMessageDOM('user', finalPrompt, null, attachedImage ? URL.createObjectURL(attachedImage) : null);

    // Save in conversation memory
    let currentChat = conversations.find(c => c.id === activeChatId);
    if (!currentChat) {
      const generatedTitle = rawText.slice(0, 32) || 'Yangi suhbat';
      currentChat = {
        id: activeChatId || ('chat-' + Date.now()),
        title: generatedTitle,
        messages: []
      };
      activeChatId = currentChat.id;
      conversations.unshift(currentChat);
    } else if (currentChat.messages.length === 0) {
      currentChat.title = rawText.slice(0, 32) || currentChat.title;
    }

    currentChat.messages.push({ role: 'user', content: finalPrompt });
    saveConversations(currentChat);
    renderHistoryList();
    currentChatTitle.textContent = currentChat.title;

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    clearAttachment();

    // Show thinking bubble
    isGenerating = true;
    thinkingStatusText.textContent = "Mahliyo javob tayyorlamoqda";
    thinkingBubble.style.display = 'flex';
    sendBtn.disabled = true;
    stopGeneratingBtn.style.display = 'flex';
    scrollChatToBottom();

    // Prepare API payload
    const apiKey = localStorage.getItem('mahliyo_gemini_key') || '';
    const modelName = localStorage.getItem('mahliyo_model') || 'gemini-3.5-flash';
    const systemPrompt = localStorage.getItem('mahliyo_system_prompt') || '';

    let streamingRow = null;
    let streamedReply = '';
    let legacyRequestStarted = false;
    activeChatAbortController = new AbortController();
    try {
      const imagePayload = attachedImage ? await readImageAsBase64(attachedImage) : null;
      const payload = {
        message: finalPrompt,
        history: currentChat.messages.slice(0, -1),
        api_key: apiKey,
        model_name: modelName,
        system_prompt: systemPrompt,
        image: imagePayload,
        use_search: useSearch
      };
      const signal = activeChatAbortController.signal;
      const requestFallback = () => {
        legacyRequestStarted = true;
        return requestLegacyChat(payload, signal);
      };
      let response;
      let data;

      try {
        response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal
        });
        const contentType = response.headers.get('Content-Type') || '';
        if (response.ok && contentType.toLowerCase().includes('text/event-stream')) {
          try {
            const streamResult = await readChatStream(response, (chunk, fullText) => {
              streamedReply = fullText;
              if (!streamingRow) streamingRow = appendMessageDOM('assistant', '');
              updateStreamingMessage(streamingRow, fullText);
              thinkingStatusText.textContent = 'Javob yozilmoqda...';
            });
            streamedReply = streamResult.text;
            data = { reply: streamedReply, artifact: null, sources: streamResult.sources };
          } catch (streamError) {
            if (signal.aborted) throw streamError;
            if (streamingRow) streamingRow.remove();
            streamingRow = null;
            streamedReply = '';
            ({ response, data } = await requestFallback());
          }
        } else {
          ({ response, data } = await requestFallback());
        }
      } catch (error) {
        if (signal.aborted) throw error;
        if (legacyRequestStarted) throw error;
        if (streamingRow) streamingRow.remove();
        streamingRow = null;
        streamedReply = '';
        ({ response, data } = await requestFallback());
      }

      thinkingBubble.style.display = 'none';

      if (response.ok && data.reply) {
        if (streamingRow) {
          updateStreamingMessage(streamingRow, data.reply, data.sources);
        } else {
          appendMessageDOM('assistant', data.reply, data.artifact, null, data.sources);
        }
        currentChat.messages.push({
          role: 'assistant',
          content: data.reply,
          artifact: data.artifact,
          sources: data.sources || []
        });
        saveConversations(currentChat);
      } else {
        const errMsg = data.error || "Noma'lum xatolik yuz berdi.";
        appendMessageDOM('assistant', `⚠️ **Xatolik:** ${errMsg}`);
      }
    } catch (err) {
      thinkingBubble.style.display = 'none';
      if (activeChatAbortController?.signal.aborted) {
        if (streamingRow && streamedReply) {
          updateStreamingMessage(streamingRow, streamedReply);
          currentChat.messages.push({ role: 'assistant', content: streamedReply });
          saveConversations(currentChat);
        } else if (streamingRow) {
          streamingRow.remove();
        }
      } else {
        appendMessageDOM('assistant', `⚠️ **Aloqa xatosi:** Server bilan bog'lanib bo'lmadi (${err.message})`);
      }
    } finally {
      activeChatAbortController = null;
      isGenerating = false;
      thinkingBubble.style.display = 'none';
      sendBtn.disabled = false;
      stopGeneratingBtn.style.display = 'none';
      scrollChatToBottom();
      messageInput.focus();
    }
  }

  // --- Attachments ---
  function readImageAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result;
        if (typeof dataUrl !== 'string' || !dataUrl.includes(',')) {
          reject(new Error("Rasmni o'qib bo'lmadi."));
          return;
        }
        resolve({
          mime_type: file.type,
          data: dataUrl.slice(dataUrl.indexOf(',') + 1)
        });
      };
      reader.onerror = () => reject(new Error("Rasmni o'qishda xatolik yuz berdi."));
      reader.readAsDataURL(file);
    });
  }

  attachmentBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      attachedFile = e.target.files[0];
      attachedFileName.textContent = attachedFile.name;
      filePreviewBar.style.display = 'flex';
    }
  });

  removeAttachmentBtn.addEventListener('click', clearAttachment);

  function clearAttachment() {
    attachedFile = null;
    fileInput.value = '';
    filePreviewBar.style.display = 'none';
  }

  // --- Form & Input Auto-resize ---
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSend();
  });

  stopGeneratingBtn.addEventListener('click', () => {
    activeChatAbortController?.abort();
  });

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + 'px';
  });

  // --- Prompt Card Clicks ---
  document.querySelectorAll('.prompt-card').forEach((card) => {
    card.addEventListener('click', () => {
      const prompt = card.getAttribute('data-prompt');
      messageInput.value = prompt;
      messageInput.focus();
      if (prompt.endsWith(': ') || prompt.endsWith('Mavzu: ')) {
        messageInput.setSelectionRange(prompt.length, prompt.length);
      } else {
        handleSend();
      }
    });
  });

  // --- New Chat & Clear Chat ---
  newChatBtn.addEventListener('click', startNewChat);
  mobileNewChatBtn.addEventListener('click', () => {
    startNewChat();
    closeMobileSidebar();
  });

  clearChatBtn.addEventListener('click', () => {
    if (confirm("Ushbu suhbat tarixini tozalashni xohlaysizmi?")) {
      const currentChat = conversations.find(c => c.id === activeChatId);
      if (currentChat) {
        currentChat.messages = [];
        saveConversations(currentChat);
        startNewChat();
      }
    }
  });

  // --- Mobile Sidebar Controls ---
  mobileMenuBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
    sidebarBackdrop.classList.add('active');
  });

  sidebarBackdrop.addEventListener('click', closeMobileSidebar);

  function closeMobileSidebar() {
    sidebar.classList.remove('open');
    sidebarBackdrop.classList.remove('active');
  }

  // --- Settings Modal ---
  const openModal = () => {
    settingsModal.style.display = 'flex';
    keyStatusAlert.style.display = 'none';
  };
  const closeModal = () => {
    settingsModal.style.display = 'none';
  };

  function showAuthMessage(message, type = 'error') {
    authStatusAlert.className = `alert-box ${type}`;
    authStatusAlert.textContent = message;
    authStatusAlert.style.display = 'block';
    authMessageWrap.style.display = 'block';
  }

  function openAuthModal() {
    authModal.style.display = 'flex';
    authStatusAlert.style.display = 'none';
  }

  function closeAuthModal() {
    authModal.style.display = 'none';
  }

  authTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const selectedTab = tab.dataset.authTab;
      authTabs.forEach((item) => item.classList.toggle('active', item === tab));
      loginForm.style.display = selectedTab === 'login' ? 'flex' : 'none';
      registerForm.style.display = selectedTab === 'register' ? 'flex' : 'none';
      authStatusAlert.style.display = 'none';
      authMessageWrap.style.display = 'none';
    });
  });

  async function submitAuthForm(form, endpoint) {
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: formData.get('email'),
          password: formData.get('password')
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Akkaunt so‘rovi bajarilmadi.');

      authUser = data.user;
      updateAuthUi();
      await loadAccountConversations();
      form.reset();
      closeAuthModal();
    } catch (error) {
      showAuthMessage(error.message);
    } finally {
      submitButton.disabled = false;
    }
  }

  loginForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitAuthForm(loginForm, '/api/auth/login');
  });

  registerForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitAuthForm(registerForm, '/api/auth/register');
  });

  openSettingsBtn.addEventListener('click', async () => {
    if (!authUser) {
      openAuthModal();
      return;
    }
    try {
      const response = await fetch('/api/auth/logout', { method: 'POST' });
      if (!response.ok) throw new Error('Akkauntdan chiqib bo‘lmadi.');
      authUser = null;
      updateAuthUi();
      loadGuestConversations();
      startNewChat();
    } catch (error) {
      console.error('Akkauntdan chiqish xatosi:', error);
    }
  });

  topSettingsBtn.addEventListener('click', openModal);
  closeSettingsBtn.addEventListener('click', closeModal);
  closeAuthModalBtn.addEventListener('click', closeAuthModal);

  settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) closeModal();
  });
  authModal.addEventListener('click', (e) => {
    if (e.target === authModal) closeAuthModal();
  });

  toggleApiKeyVisBtn.addEventListener('click', () => {
    if (geminiApiKeyInput.type === 'password') {
      geminiApiKeyInput.type = 'text';
      toggleApiKeyVisBtn.textContent = "Yashirish";
    } else {
      geminiApiKeyInput.type = 'password';
      toggleApiKeyVisBtn.textContent = "Ko'rish";
    }
  });

  saveSettingsBtn.addEventListener('click', () => {
    const key = geminiApiKeyInput.value.trim();
    const model = modelSelect.value;
    const prompt = systemPromptInput.value.trim();

    localStorage.setItem('mahliyo_gemini_key', key);
    localStorage.setItem('mahliyo_model', model);
    localStorage.setItem('mahliyo_system_prompt', prompt);

    updateModelTag(key, model);
    closeModal();
  });

  testKeyBtn.addEventListener('click', async () => {
    const key = geminiApiKeyInput.value.trim();
    testKeyBtn.textContent = "Tekshirilmoqda...";
    testKeyBtn.disabled = true;

    try {
      const res = await fetch('/api/test-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json();
      if (res.ok && data.valid) {
        keyStatusAlert.className = 'alert-box success';
        keyStatusAlert.textContent = "✅ Kalit muvaffaqiyatli tekshirildi va yaroqli!";
      } else {
        keyStatusAlert.className = 'alert-box error';
        keyStatusAlert.textContent = `❌ ${data.error || "Kalit yaroqsiz."}`;
      }
    } catch (e) {
      keyStatusAlert.className = 'alert-box error';
      keyStatusAlert.textContent = "Server bilan aloqa xatosi.";
    } finally {
      keyStatusAlert.style.display = 'block';
      testKeyBtn.textContent = "Kalitni tekshirish";
      testKeyBtn.disabled = false;
    }
  });

  // --- Initialize App ---
  loadStoredSettings();
  loadGuestConversations();
  startNewChat();
  initializeAuth();
});
