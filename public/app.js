const feedList = document.getElementById('feed-list');
const composer = document.getElementById('composer');
const contentInput = document.getElementById('post-content');
const locationInput = document.getElementById('post-location');
const authToggle = document.getElementById('auth-toggle');
const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const appTopbar = document.getElementById('app-topbar');
const featuresSection = document.getElementById('features');
const registerForm = document.getElementById('register-form');
const loginForm = document.getElementById('login-form');
const authStatus = document.getElementById('auth-status');
const logoutBtn = document.getElementById('logout-btn');
const openLogin = document.getElementById('open-login');
const profileHandle = document.getElementById('profile-handle');
const profileMeta = document.getElementById('profile-meta');
const followButtons = document.querySelectorAll('.follow-btn');
const openComposer = document.getElementById('open-composer');

const storageKey = 'berendeiPosts';
const userKey = 'berendeiUser';

const defaultPosts = [];

const loadPosts = () => {
  const saved = localStorage.getItem(storageKey);
  if (!saved) {
    localStorage.setItem(storageKey, JSON.stringify(defaultPosts));
    return [...defaultPosts];
  }
  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : [...defaultPosts];
  } catch (error) {
    return [...defaultPosts];
  }
};

let posts = loadPosts();
let currentUser = JSON.parse(localStorage.getItem(userKey) || 'null');

const savePosts = () => {
  localStorage.setItem(storageKey, JSON.stringify(posts));
};

const saveUser = () => {
  localStorage.setItem(userKey, JSON.stringify(currentUser));
};

const updateAuthUI = () => {
  if (currentUser) {
    authStatus.textContent = `Вы вошли как ${currentUser.handle}.`;
    authToggle.textContent = 'Профиль';
    profileHandle.textContent = currentUser.handle;
    profileMeta.textContent = `${currentUser.name} · ${currentUser.email}`;
    logoutBtn.style.display = 'inline-flex';
    authGate.classList.add('app-hidden');
    appShell.classList.remove('app-hidden');
    appTopbar.classList.remove('app-hidden');
    featuresSection.classList.remove('app-hidden');
  } else {
    authStatus.textContent = 'Пока вы не вошли.';
    authToggle.textContent = 'Войти';
    profileHandle.textContent = 'berendei_official';
    profileMeta.textContent = '124 публикации · 8,7k подписчиков';
    logoutBtn.style.display = 'none';
    authGate.classList.remove('app-hidden');
    appShell.classList.add('app-hidden');
    appTopbar.classList.add('app-hidden');
    featuresSection.classList.add('app-hidden');
  }
};

const createPostCard = (post) => {
  const article = document.createElement('article');
  article.className = 'feed-item';
  article.dataset.postId = post.id;

  article.innerHTML = `
    <div class="feed-header">
      <div class="avatar small"></div>
      <div>
        <strong>${post.author}</strong>
        <span>${post.time} · ${post.location || 'Онлайн'}</span>
      </div>
    </div>
    <div class="post-preview">${post.preview}</div>
    <p>${post.content}</p>
    <div class="feed-actions">
      <button type="button" class="like-btn">${post.liked ? '💙' : '❤️'} ${post.likes}</button>
      <span>💬 ${post.comments.length}</span>
      <button type="button" class="share-btn">🔁 Поделиться</button>
    </div>
    <div class="comment-list">
      ${post.comments.map((comment) => `<div>• ${comment}</div>`).join('')}
    </div>
    <form class="comment-form">
      <input type="text" name="comment" placeholder="Написать комментарий..." required />
      <button type="submit">Отправить</button>
    </form>
  `;

  return article;
};

const renderPosts = () => {
  feedList.innerHTML = '';
  posts.forEach((post) => {
    feedList.appendChild(createPostCard(post));
  });
};

const addPost = (event) => {
  event.preventDefault();
  if (!currentUser) {
    authStatus.textContent = 'Сначала войдите, чтобы публиковать посты.';
    authGate.scrollIntoView({ behavior: 'smooth' });
    return;
  }
  const content = contentInput.value.trim();
  if (!content) return;

  const location = locationInput.value.trim();
  const newPost = {
    id: `post-${Date.now()}`,
    author: currentUser.handle,
    location: location || 'Онлайн',
    content,
    preview: 'Новый пост от вашего аккаунта',
    likes: 0,
    liked: false,
    comments: [],
    time: 'Только что',
  };

  posts = [newPost, ...posts];
  savePosts();
  renderPosts();
  composer.reset();
};

const handleFeedClick = (event) => {
  const card = event.target.closest('.feed-item');
  if (!card) return;
  const postId = card.dataset.postId;
  const post = posts.find((item) => item.id === postId);
  if (!post) return;

  if (event.target.classList.contains('like-btn')) {
    post.liked = !post.liked;
    post.likes += post.liked ? 1 : -1;
    savePosts();
    renderPosts();
  }

  if (event.target.classList.contains('share-btn')) {
    navigator.clipboard?.writeText(`${post.content}`);
    event.target.textContent = '✅ Ссылка скопирована';
    setTimeout(() => {
      event.target.textContent = '🔁 Поделиться';
    }, 1500);
  }
};

const handleCommentSubmit = (event) => {
  if (!event.target.classList.contains('comment-form')) return;
  event.preventDefault();
  if (!currentUser) {
    authStatus.textContent = 'Войдите, чтобы оставлять комментарии.';
    authGate.scrollIntoView({ behavior: 'smooth' });
    return;
  }
  const card = event.target.closest('.feed-item');
  if (!card) return;
  const postId = card.dataset.postId;
  const post = posts.find((item) => item.id === postId);
  if (!post) return;
  const input = event.target.querySelector('input[name="comment"]');
  const comment = input.value.trim();
  if (!comment) return;
  post.comments.push(comment);
  savePosts();
  renderPosts();
};

const handleRegister = (event) => {
  event.preventDefault();
  const name = document.getElementById('register-name').value.trim();
  const handleInput = document.getElementById('register-handle').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value.trim();
  if (!name || !handleInput || !email || !password) return;

  currentUser = {
    name,
    handle: handleInput.startsWith('@') ? handleInput : `@${handleInput}`,
    email,
  };
  saveUser();
  updateAuthUI();
  registerForm.reset();
};

const handleLogin = (event) => {
  event.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  if (!email || !password) return;

  currentUser = currentUser || {
    name: 'Пользователь',
    handle: '@berendei_user',
    email,
  };
  saveUser();
  updateAuthUI();
  loginForm.reset();
};

const handleLogout = () => {
  currentUser = null;
  saveUser();
  updateAuthUI();
};

const handleFollow = (event) => {
  const button = event.target.closest('.follow-btn');
  if (!button) return;
  if (!currentUser) {
    authStatus.textContent = 'Войдите, чтобы подписываться.';
    authGate.scrollIntoView({ behavior: 'smooth' });
    return;
  }
  button.textContent = button.textContent === 'Подписаться' ? 'Вы подписаны' : 'Подписаться';
};

openComposer.addEventListener('click', () => {
  composer.scrollIntoView({ behavior: 'smooth' });
  contentInput.focus();
});
composer.addEventListener('submit', addPost);
feedList.addEventListener('click', handleFeedClick);
feedList.addEventListener('submit', handleCommentSubmit);
registerForm.addEventListener('submit', handleRegister);
loginForm.addEventListener('submit', handleLogin);
logoutBtn.addEventListener('click', handleLogout);
followButtons.forEach((button) => button.addEventListener('click', handleFollow));
authToggle.addEventListener('click', () => {
  authGate.scrollIntoView({ behavior: 'smooth' });
});
openLogin.addEventListener('click', () => {
  document.getElementById('login-email').focus();
});

renderPosts();
updateAuthUI();
