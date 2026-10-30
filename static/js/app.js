/**
 * Mahliyo AI — Front-End Application Logic v1.1
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

  // --- State ---
  let activeChatId = null;
  let conversations = [];
  let attachedFile = null;
  let isGenerating = false;
  let isRecordingVoice = false;
  let speechRecognition = null;
  let currentSpeakingUtterance = null;

  // Active slide deck state
  let currentSlideDeck = [];
  let currentSlideIndex = 0;

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
    const model = localStorage.getItem('mahliyo_model') || 'gemini-1.5-flash';
    const prompt = localStorage.getItem('mahliyo_system_prompt') || '';

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
      modelStatusTag.textContent = 'Mahliyo v1.1';
      modelStatusTag.style.color = 'var(--text-dim)';
    }
  }

  function loadConversations() {
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

  function saveConversations() {
    localStorage.setItem('mahliyo_conversations', JSON.stringify(conversations));
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

  function selectConversation(id) {
    activeChatId = id;
    const chat = conversations.find(c => c.id === id);
    if (!chat) return;

    currentChatTitle.textContent = chat.title;
    renderHistoryList();

    if (chat.messages && chat.messages.length > 0) {
      welcomeHero.style.display = 'none';
      messagesContainer.innerHTML = '';
      chat.messages.forEach(msg => appendMessageDOM(msg.role, msg.content, msg.artifact));
      scrollChatToBottom();
    } else {
      startNewChat();
    }
  }

  function deleteConversation(id) {
    conversations = conversations.filter(c => c.id !== id);
    saveConversations();
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
  function appendMessageDOM(role, text, artifact = null) {
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
        }
      }

      row.innerHTML = `
        <div class="msg-avatar bot">
          <img src="/static/images/logo.svg" alt="Mahliyo">
        </div>
        <div class="message-bubble">
          <div class="msg-body">${formatMarkdown(text)}</div>
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
        navigator.clipboard.writeText(text).then(() => {
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
        speakText(text, ttsBtn);
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
    }

    messagesContainer.appendChild(row);

    // Highlight code blocks
    row.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
      addCodeCopyBtn(block);
    });

    scrollChatToBottom();
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
  function speakText(text, btnElement) {
    if (!('speechSynthesis' in window)) {
      alert("Brauzeringizda nutq sintezi qo'llab-quvvatlanmaydi.");
      return;
    }

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = "Ovozli eshitish";
      }
      return;
    }

    // Strip markdown formatting symbols for natural reading
    const clean = text.replace(/[#*`_~\[\]\(\)\>]/g, ' ').replace(/\n+/g, '. ');
    const utter = new SpeechSynthesisUtterance(clean);
    utter.lang = 'uz-UZ';
    utter.rate = 1.0;
    utter.pitch = 1.05;

    // Pick a pleasant voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('uz') || v.lang.startsWith('tr') || v.lang.startsWith('ru'));
    if (preferredVoice) utter.voice = preferredVoice;

    if (btnElement) {
      btnElement.classList.add('playing');
      btnElement.querySelector('span').textContent = "To'xtatish";
    }

    utter.onend = () => {
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = "Ovozli eshitish";
      }
    };

    utter.onerror = () => {
      if (btnElement) {
        btnElement.classList.remove('playing');
        btnElement.querySelector('span').textContent = "Ovozli eshitish";
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
    const topic = prompt("Taqdimot (slayd) mavzusini kiriting:", "Sun'iy intellekt va uning istiqbollari");
    if (topic && topic.trim()) {
      messageInput.value = `Menga quyidagi mavzuda professional taqdimot (slayd) va .pptx fayl tayyorlab ber: ${topic.trim()}`;
      handleSend();
      closeMobileSidebar();
    }
  });

  quickDocBtn.addEventListener('click', () => {
    const topic = prompt("Mustaqil ish (Word .docx) mavzusini kiriting:", "Zamonaviy dasturlash tillari va ularning tahlili");
    if (topic && topic.trim()) {
      messageInput.value = `Menga OTM standarti bo'yicha to'liq mustaqil ish (Word .docx) yozib ber: ${topic.trim()}`;
      handleSend();
      closeMobileSidebar();
    }
  });

  // --- Sending Message & Chat API ---
  async function handleSend() {
    const rawText = messageInput.value.trim();
    if (!rawText && !attachedFile) return;
    if (isGenerating) return;

    let finalPrompt = rawText;
    if (attachedFile) {
      finalPrompt = `[Ilova qilingan fayl: ${attachedFile.name}]\n` + finalPrompt;
    }

    // Hide welcome hero on first message
    welcomeHero.style.display = 'none';

    // Append User Message
    appendMessageDOM('user', finalPrompt);

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
    saveConversations();
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
    scrollChatToBottom();

    // Prepare API payload
    const apiKey = localStorage.getItem('mahliyo_gemini_key') || '';
    const modelName = localStorage.getItem('mahliyo_model') || 'gemini-1.5-flash';
    const systemPrompt = localStorage.getItem('mahliyo_system_prompt') || '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: finalPrompt,
          history: currentChat.messages.slice(0, -1),
          api_key: apiKey,
          model_name: modelName,
          system_prompt: systemPrompt
        })
      });

      const data = await response.json();
      thinkingBubble.style.display = 'none';

      if (response.ok && data.reply) {
        appendMessageDOM('assistant', data.reply, data.artifact);
        currentChat.messages.push({ role: 'assistant', content: data.reply, artifact: data.artifact });
        saveConversations();
      } else {
        const errMsg = data.error || "Noma'lum xatolik yuz berdi.";
        appendMessageDOM('assistant', `⚠️ **Xatolik:** ${errMsg}`);
      }
    } catch (err) {
      thinkingBubble.style.display = 'none';
      appendMessageDOM('assistant', `⚠️ **Aloqa xatosi:** Server bilan bog'lanib bo'lmadi (${err.message})`);
    } finally {
      isGenerating = false;
      sendBtn.disabled = false;
      scrollChatToBottom();
      messageInput.focus();
    }
  }

  // --- Attachments ---
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
        saveConversations();
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

  openSettingsBtn.addEventListener('click', openModal);
  topSettingsBtn.addEventListener('click', openModal);
  closeSettingsBtn.addEventListener('click', closeModal);

  settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) closeModal();
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
    if (!key) {
      keyStatusAlert.className = 'alert-box error';
      keyStatusAlert.textContent = "Iltimos, avval API kalitni kiriting.";
      keyStatusAlert.style.display = 'block';
      return;
    }

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
  loadConversations();
  startNewChat();
});
